# shop/views.py

"""
======================== GUIDE DE CRÉATION D'UN UTILISATEUR STAFF ========================

Pour créer un utilisateur staff (administrateur) pour gérer la boutique, suivez ces étapes :

1. VIA DJANGO ADMIN (Méthode recommandée) :
   - Créez d'abord un superutilisateur : python manage.py createsuperuser
   - Connectez-vous à /admin/ avec ce compte
   - Allez dans "Utilisateurs"
   - Créez un nouvel utilisateur ou modifiez un utilisateur existant
   - Cochez la case "Statut staff" pour donner les droits d'administration
   - Sauvegardez

2. VIA LE SHELL DJANGO :
   python manage.py shell
   >>> from django.contrib.auth.models import User
   >>> user = User.objects.create_user(username='admin', email='admin@example.com', password='motdepasse')
   >>> user.is_staff = True
   >>> user.save()

3. VIA UNE COMMANDE PERSONNALISÉE :
   Créez un fichier management/commands/create_staff.py dans votre app shop :

   from django.core.management.base import BaseCommand
   from django.contrib.auth.models import User

   class Command(BaseCommand):
       def handle(self, *args, **kwargs):
           user = User.objects.create_user(
               username='staff_user',
               email='staff@example.com',
               password='password123'
           )
           user.is_staff = True
           user.save()
           self.stdout.write('Staff user created successfully!')

   Puis exécutez : python manage.py create_staff

4. PERMISSIONS DU STAFF :
   Un utilisateur avec is_staff=True peut accéder aux fonctionnalités suivantes :
   - Dashboard admin (/admin/dashboard/)
   - Gestion des produits (ajouter, modifier, supprimer)
   - Gestion des catégories
   - Gestion des commandes (voir et modifier le statut)
   - Voir les messages de contact

   Le décorateur @staff_required vérifie automatiquement ces permissions.

5. DIFFÉRENCE ENTRE STAFF ET SUPERUSER :
   - is_staff=True : Accès aux fonctions d'administration de la boutique
   - is_superuser=True : Accès complet à tout le système Django (recommandé pour le propriétaire uniquement)

========================================================================================
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Count, Sum, Avg
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import json
import logging

from .models import Product, Category, Cart, CartItem, Order, OrderItem, Contact, ProductImage, Size
from .forms import ProductForm, CategoryForm, ProductImageForm

logger = logging.getLogger(__name__)


# ======================== FONCTIONS UTILITAIRES ========================

def get_or_create_cart(request):
    """Obtient ou crée un panier pour l'utilisateur actuel"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    return cart


def is_staff(user):
    """Vérifie si l'utilisateur est admin"""
    return user.is_staff


# ======================== VUES PUBLIQUES ========================

def index(request):
    """Page d'accueil"""
    products = Product.objects.filter(sold_out=False).select_related('category').prefetch_related('images')[:6]
    categories = Category.objects.all()
    context = {
        'products': products,
        'categories': categories,
    }
    return render(request, 'shop/index.html', context)


def shop(request):
    """Page boutique avec tous les produits"""
    products = Product.objects.filter(sold_out=False).select_related('category').prefetch_related('images', 'sizes')
    categories = Category.objects.annotate(product_count=Count('products'))
    
    # Filtrer par catégorie
    category_filter = request.GET.get('category')
    if category_filter and category_filter != 'all':
        products = products.filter(category__id=category_filter)
    
    # Recherche
    search_query = request.GET.get('q')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Tri
    sort = request.GET.get('sort')
    if sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    elif sort == 'name':
        products = products.order_by('name')
    elif sort == 'newest':
        products = products.order_by('-created_at')
    
    context = {
        'products': products,
        'categories': categories,
        'current_category': category_filter,
        'search_query': search_query,
    }
    return render(request, 'shop/shop.html', context)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

def product_detail(request, product_id):
    """Détail d'un produit"""
    try:
        product = get_object_or_404(Product, id=product_id)
        
        # Vérifier si le produit est épuisé
        if product.sold_out:
            messages.warning(request, f"Le produit '{product.name}' est actuellement épuisé.")
        
        # Récupérer des produits similaires
        related_products = Product.objects.filter(
            category=product.category,
            sold_out=False
        ).exclude(id=product.id)[:4]
        
        context = {
            'product': product,
            'related_products': related_products,
        }
        return render(request, 'shop/item.html', context)
        
    except:
        messages.error(request, "Le produit demandé n'existe pas.")
        return redirect('shop:shop')

def cart_view(request):
    """Vue du panier"""
    cart = get_or_create_cart(request)
    context = {
        'cart': cart,
    }
    return render(request, 'shop/cart.html', context)


@csrf_exempt
def add_to_cart(request):
    """Ajouter au panier (AJAX)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            quantity = data.get('quantity', 1)
            selected_size = data.get('selected_size', '')  # Valeur par défaut vide
            
            # Si size_id est envoyé au lieu de selected_size
            size_id = data.get('size_id')
            if size_id:
                try:
                    size = Size.objects.get(id=size_id)
                    selected_size = size.name
                except Size.DoesNotExist:
                    selected_size = ''
            
            product = get_object_or_404(Product, id=product_id)
            cart = get_or_create_cart(request)
            
            # Vérifier le stock
            if product.quantity < quantity:
                return JsonResponse({
                    'success': False,
                    'message': f'Stock insuffisant! Seulement {product.quantity} unités disponibles.'
                })
            
            # Obtenir ou créer l'article du panier avec selected_size toujours défini
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                selected_size=selected_size or '',  # S'assurer que ce n'est jamais None
                defaults={'quantity': quantity}
            )
            
            if not created:
                # Vérifier si l'ajout ne dépasse pas le stock
                if cart_item.quantity + quantity > product.quantity:
                    return JsonResponse({
                        'success': False,
                        'message': f'Stock insuffisant! Vous avez déjà {cart_item.quantity} dans votre panier.'
                    })
                cart_item.quantity += quantity
                cart_item.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Produit ajouté au panier!',
                'cart_count': cart.items.count()
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erreur: {str(e)}'
            })


@csrf_exempt
def update_cart_item(request):
    """Mettre à jour la quantité d'un article (AJAX)"""
    if request.method == 'POST':
        data = json.loads(request.body)
        item_id = data.get('item_id')
        quantity = data.get('quantity')
        
        cart_item = get_object_or_404(CartItem, id=item_id)
        
        if quantity <= 0:
            cart_item.delete()
        else:
            if quantity > cart_item.product.quantity:
                return JsonResponse({
                    'success': False,
                    'message': 'Stock insuffisant!'
                })
            cart_item.quantity = quantity
            cart_item.save()
        
        cart = get_or_create_cart(request)
        return JsonResponse({
            'success': True,
            'cart_total': str(cart.get_total()),
            'cart_count': cart.items.count()
        })


@csrf_exempt
def remove_from_cart(request):
    """Retirer du panier (AJAX)"""
    if request.method == 'POST':
        data = json.loads(request.body)
        item_id = data.get('item_id')
        
        cart_item = get_object_or_404(CartItem, id=item_id)
        cart_item.delete()
        
        cart = get_or_create_cart(request)
        return JsonResponse({
            'success': True,
            'cart_total': str(cart.get_total()),
            'cart_count': cart.items.count()
        })


def checkout(request):
    """Page de commande améliorée"""
    cart = get_or_create_cart(request)

    # Vérifier si le panier est vide
    if not cart.items.exists():
        messages.warning(request, 'Votre panier est vide.')
        return redirect('shop:cart')

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Récupérer les données du formulaire
                customer_name = request.POST.get('customer_name', '')
                customer_email = request.POST.get('customer_email', '')
                customer_phone = request.POST.get('customer_phone', '')
                customer_address = request.POST.get('customer_address', '')
                payment_method = request.POST.get('payment_method', 'cash')

                # Utiliser les infos de l'utilisateur connecté si disponibles
                if request.user.is_authenticated:
                    if not customer_name:
                        customer_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
                    if not customer_email:
                        customer_email = request.user.email

                # Validation des données
                if not customer_name or not customer_phone or not customer_address:
                    messages.error(request, 'Veuillez remplir tous les champs obligatoires.')
                    return render(request, 'shop/checkout.html', {'cart': cart})

                # Créer la commande
                order = Order.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    customer_name=customer_name,
                    customer_email=customer_email,
                    customer_phone=customer_phone,
                    customer_address=customer_address,
                    payment_method=payment_method,
                    total_amount=cart.get_total(),
                    status='pending'
                )

                # Créer les articles de commande et mettre à jour le stock
                for cart_item in cart.items.all():
                    # Vérifier le stock disponible
                    if cart_item.product.quantity < cart_item.quantity:
                        raise ValueError(f"Stock insuffisant pour {cart_item.product.name}")

                    OrderItem.objects.create(
                        order=order,
                        product=cart_item.product,
                        quantity=cart_item.quantity,
                        price=cart_item.product.get_current_price(),
                        selected_size=cart_item.selected_size or ''
                    )

                    # Mettre à jour le stock du produit
                    cart_item.product.quantity -= cart_item.quantity
                    if cart_item.product.quantity == 0:
                        cart_item.product.sold_out = True
                    cart_item.product.save()

                # Vider le panier
                cart.items.all().delete()

                # Envoyer un email de confirmation si configuré
                if customer_email and hasattr(settings, 'EMAIL_HOST_USER') and settings.EMAIL_HOST_USER:
                    try:
                        send_mail(
                            f'Commande #{order.id} confirmée',
                            f'Votre commande a été confirmée. Total: {order.total_amount} F CFA',
                            settings.DEFAULT_FROM_EMAIL,
                            [customer_email],
                            fail_silently=True,
                        )
                    except Exception as e:
                        logger.error(f"Erreur envoi email: {e}")

                messages.success(request, f'Commande #{order.id} passée avec succès!')
                return redirect('shop:index')

        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Erreur lors de la commande: {str(e)}')
            logger.error(f"Erreur checkout: {e}")

    context = {
        'cart': cart,
        'cart_items': cart.items.all(),
        'total': cart.get_total(),
    }
    return render(request, 'shop/checkout.html', context)


def contact_view(request):
    """Page de contact"""
    if request.method == 'POST':
        Contact.objects.create(
            name=request.POST.get('name'),
            email=request.POST.get('email', ''),
            phone=request.POST.get('phone', ''),
            message=request.POST.get('message')
        )
        messages.success(request, 'Votre message a été envoyé avec succès! Nous vous répondrons dans les plus brefs délais.')
        return redirect('shop:contact')

    return render(request, 'shop/contact.html')


# ======================== VUES AUTHENTIFICATION ========================

def login_register_view(request):
    """Vue pour afficher la page de connexion/inscription"""
    if request.user.is_authenticated:
        return redirect('shop:index')
    return render(request, 'shop/login.html')


@csrf_exempt
def ajax_login(request):
    """Vue AJAX pour la connexion"""
    if request.method == 'POST':
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')
        
        try:
            user = User.objects.get(email=email)
            user = authenticate(request, username=user.username, password=password)
            
            if user is not None:
                login(request, user)
                return JsonResponse({
                    'success': True,
                    'message': 'Connexion réussie!',
                    'redirect_url': '/home/'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Email ou mot de passe incorrect!'
                })
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Aucun compte trouvé avec cet email!'
            })
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})


@csrf_exempt
def ajax_register(request):
    """Vue AJAX pour l'inscription"""
    if request.method == 'POST':
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        
        if password != confirm_password:
            return JsonResponse({
                'success': False,
                'message': 'Les mots de passe ne correspondent pas!'
            })
        
        if User.objects.filter(email=email).exists():
            return JsonResponse({
                'success': False,
                'message': 'Un compte existe déjà avec cet email!'
            })
        
        try:
            username = email.split('@')[0]
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            login(request, user)
            
            return JsonResponse({
                'success': True,
                'message': 'Inscription réussie!',
                'redirect_url': '/home/'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erreur lors de l\'inscription: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})


def logout_view(request):
    """Vue pour la déconnexion"""
    logout(request)
    messages.success(request, 'Vous avez été déconnecté avec succès!')
    return redirect('shop:login')


# ======================== VUES COMPTE UTILISATEUR ========================

@login_required
def user_profile(request):
    """Vue pour le profil utilisateur"""
    if request.method == 'POST':
        # Mise à jour du profil
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', user.email)

        # Changement de mot de passe si fourni
        new_password = request.POST.get('new_password')
        if new_password:
            current_password = request.POST.get('current_password')
            if user.check_password(current_password):
                user.set_password(new_password)
                messages.success(request, 'Mot de passe modifié avec succès!')
                # Re-login après changement de mot de passe
                login(request, user)
            else:
                messages.error(request, 'Mot de passe actuel incorrect!')

        user.save()
        messages.success(request, 'Profil mis à jour avec succès!')
        return redirect('shop:user_profile')

    # Statistiques de l'utilisateur
    user_orders = Order.objects.filter(user=request.user)
    total_orders = user_orders.count()
    total_spent = user_orders.aggregate(total=Sum('total_amount'))['total'] or 0

    context = {
        'user': request.user,
        'total_orders': total_orders,
        'total_spent': total_spent,
        'recent_orders': user_orders[:5],
    }
    return render(request, 'shop/user_profile.html', context)


@login_required
def user_orders(request):
    """Vue pour afficher les commandes de l'utilisateur"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    # Pagination
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'orders': page_obj,
        'page_obj': page_obj,
    }
    return render(request, 'shop/user_orders.html', context)


@csrf_exempt
def reset_password(request):
    """Vue pour réinitialiser le mot de passe"""
    if request.method == 'POST':
        data = json.loads(request.body)
        email = data.get('email')
        
        try:
            user = User.objects.get(email=email)
            return JsonResponse({
                'success': True,
                'message': 'Un lien de réinitialisation a été envoyé à votre email!'
            })
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Aucun compte trouvé avec cet email!'
            })
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})


# ======================== VUES ADMINISTRATION ========================

@login_required
def admin_dashboard(request):
    """Dashboard admin personnalisé"""
    total_products = Product.objects.count()
    total_categories = Category.objects.count()
    total_orders = Order.objects.count()
    unread_messages = Contact.objects.filter(is_read=False).count()
    
    recent_products = Product.objects.select_related('category').order_by('-created_at')[:10]
    recent_orders = Order.objects.order_by('-created_at')[:5]
    categories = Category.objects.all()
    
    context = {
        'total_products': total_products,
        'total_categories': total_categories,
        'total_orders': total_orders,
        'unread_messages': unread_messages,
        'products': recent_products,
        'orders': recent_orders,
        'categories': categories,
    }
    
    return render(request, 'shop/admin/dashboard.html', context)


# ======================== GESTION DES PRODUITS ========================

def staff_required(view_func):
    """Décorateur personnalisé pour vérifier les permissions staff"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Vous devez être connecté pour accéder à cette page.")
            return redirect('shop:login')
        if not request.user.is_staff:
            messages.error(request, "Vous n'avez pas les permissions nécessaires pour accéder à cette page.")
            return redirect('shop:index')
        return view_func(request, *args, **kwargs)
    return wrapper

@staff_required
def product_list(request):
    """Liste des produits avec pagination et filtres"""
    products = Product.objects.select_related('category').order_by('-created_at')
    
    # Filtres
    category_filter = request.GET.get('category')
    search_query = request.GET.get('q')
    status_filter = request.GET.get('status')
    
    if category_filter:
        products = products.filter(category_id=category_filter)
    
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )
    
    if status_filter == 'sold_out':
        products = products.filter(sold_out=True)
    elif status_filter == 'available':
        products = products.filter(sold_out=False)
    elif status_filter == 'low_stock':
        products = products.filter(quantity__lte=5, sold_out=False)
    
    # Pagination
    paginator = Paginator(products, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    categories = Category.objects.all()
    
    context = {
        'page_obj': page_obj,
        'products': page_obj,
        'categories': categories,
        'current_category': category_filter,
        'search_query': search_query,
        'current_status': status_filter,
    }
    
    return render(request, 'shop/admin/product_list.html', context)


@staff_required
def product_add(request):
    """Ajouter un nouveau produit"""
    if request.method == 'POST':
        try:
            # Récupération manuelle des données
            name = request.POST.get('name')
            description = request.POST.get('description')
            category_id = request.POST.get('category')
            price = request.POST.get('price')
            sale_price = request.POST.get('sale_price')
            quantity = request.POST.get('quantity', 1)
            on_sale = request.POST.get('on_sale') == 'on'
            sold_out = request.POST.get('sold_out') == 'on'

            # Validation basique
            if not name or not category_id or not price:
                messages.error(request, 'Veuillez remplir tous les champs obligatoires.')
                return redirect('shop:product_add')

            # Créer le produit
            with transaction.atomic():
                product = Product.objects.create(
                    name=name,
                    description=description or '',
                    category_id=category_id,
                    price=float(price),
                    sale_price=float(sale_price) if sale_price else None,
                    quantity=int(quantity),
                    on_sale=on_sale,
                    sold_out=sold_out
                )

                # Gestion des tailles
                sizes = request.POST.getlist('sizes')
                for size_name in sizes:
                    size, created = Size.objects.get_or_create(name=size_name)
                    product.sizes.add(size)

                # Gestion des images multiples
                images = request.FILES.getlist('images')
                for i, image in enumerate(images):
                    ProductImage.objects.create(
                        product=product,
                        image=image,
                        is_primary=(i == 0)
                    )

                messages.success(request, f'Produit "{product.name}" ajouté avec succès!')
                return redirect('shop:product_list')

        except Exception as e:
            messages.error(request, f'Erreur lors de l\'ajout du produit: {str(e)}')
            return redirect('shop:product_add')

    # GET request
    categories = Category.objects.all()
    recent_products = Product.objects.select_related('category').order_by('-created_at')[:5]

    context = {
        'categories': categories,
        'recent_products': recent_products,
    }

    return render(request, 'shop/admin/product_add.html', context)


@login_required
@user_passes_test(is_staff)
def product_edit(request, pk):
    """Modifier un produit"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    product = form.save()
                    
                    # Gestion des nouvelles images
                    new_images = request.FILES.getlist('images')
                    if new_images:
                        for i, image in enumerate(new_images):
                            ProductImage.objects.create(
                                product=product,
                                image=image,
                                is_primary=(product.images.count() == 0 and i == 0)
                            )
                    
                    messages.success(request, f'Produit "{product.name}" modifié avec succès!')
                    return redirect('shop:product_list')
                    
            except Exception as e:
                messages.error(request, f'Erreur lors de la modification: {str(e)}')
        else:
            messages.error(request, 'Veuillez corriger les erreurs ci-dessous.')
    else:
        form = ProductForm(instance=product)
    
    context = {
        'form': form,
        'product': product,
        'existing_images': product.images.all(),
    }
    
    return render(request, 'shop/admin/product_edit.html', context)


@staff_required
@require_http_methods(["POST"])
def product_delete(request, pk):
    """Supprimer un produit"""
    try:
        product = get_object_or_404(Product, pk=pk)
        product_name = product.name
        product.delete()
        
        messages.success(request, f'Produit "{product_name}" supprimé avec succès!')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Produit "{product_name}" supprimé avec succès!'
            })
        else:
            return redirect('shop:product_list')
            
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': f'Erreur lors de la suppression: {str(e)}'
            })
        else:
            messages.error(request, f'Erreur lors de la suppression: {str(e)}')
            return redirect('shop:product_list')


# ======================== GESTION DES CATÉGORIES ========================

@login_required
@user_passes_test(is_staff)
def category_list(request):
    """Liste des catégories"""
    categories = Category.objects.all().order_by('name')
    
    search_query = request.GET.get('q')
    if search_query:
        categories = categories.filter(name__icontains=search_query)
    
    paginator = Paginator(categories, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'categories': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'shop/admin/category_list.html', context)


@login_required
@user_passes_test(is_staff)
def category_add(request):
    """Ajouter une nouvelle catégorie"""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Catégorie "{category.name}" ajoutée avec succès!')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'category_id': category.id,
                    'category_name': category.name
                })
            else:
                return redirect('shop:category_list')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = []
                for field, field_errors in form.errors.items():
                    for error in field_errors:
                        errors.append(f'{field}: {error}')
                
                return JsonResponse({
                    'success': False,
                    'message': 'Erreurs de validation: ' + '; '.join(errors)
                })
            else:
                messages.error(request, 'Veuillez corriger les erreurs ci-dessous.')
    else:
        form = CategoryForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'shop/admin/category_add.html', context)


@login_required
@user_passes_test(is_staff)
def category_edit(request, pk):
    """Modifier une catégorie"""
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Catégorie "{category.name}" modifiée avec succès!')
            return redirect('shop:category_list')
        else:
            messages.error(request, 'Veuillez corriger les erreurs ci-dessous.')
    else:
        form = CategoryForm(instance=category)
    
    context = {
        'form': form,
        'category': category,
    }
    
    return render(request, 'shop/admin/category_edit.html', context)


@login_required
@user_passes_test(is_staff)
@require_http_methods(["POST"])
def category_delete(request, pk):
    """Supprimer une catégorie"""
    try:
        category = get_object_or_404(Category, pk=pk)
        
        if category.products.exists():
            message = f'Impossible de supprimer "{category.name}": des produits sont encore liés.'
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': message
                })
            else:
                messages.error(request, message)
                return redirect('shop:category_list')
        
        category_name = category.name
        category.delete()
        
        success_message = f'Catégorie "{category_name}" supprimée avec succès!'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': success_message
            })
        else:
            messages.success(request, success_message)
            return redirect('shop:category_list')
            
    except Exception as e:
        error_message = f'Erreur lors de la suppression: {str(e)}'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': error_message
            })
        else:
            messages.error(request, error_message)
            return redirect('shop:category_list')


# ======================== GESTION DES COMMANDES ========================

@login_required
@user_passes_test(is_staff)
def order_list(request):
    """Liste des commandes"""
    orders = Order.objects.select_related('user').order_by('-created_at')

    # Calculer les statistiques
    order_stats = {
        'pending': Order.objects.filter(status='pending').count(),
        'confirmed': Order.objects.filter(status='confirmed').count(),
        'delivered': Order.objects.filter(status='delivered').count(),
        'cancelled': Order.objects.filter(status='cancelled').count(),
    }

    # Filtres
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)

    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'orders': page_obj,
        'current_status': status_filter,
        'status_choices': Order.STATUS_CHOICES,
        'order_stats': order_stats,
    }

    return render(request, 'shop/admin/order_list.html', context)


@login_required
@user_passes_test(is_staff)
def order_detail(request, pk):
    """Détail d'une commande"""
    order = get_object_or_404(Order, pk=pk)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()
            messages.success(request, 'Statut de la commande mis à jour!')
    
    context = {
        'order': order,
        'status_choices': Order.STATUS_CHOICES,
    }
    
    return render(request, 'shop/admin/order_detail.html', context)


# ======================== FONCTIONS UTILITAIRES ADMIN ========================

@login_required
@user_passes_test(is_staff)
@require_http_methods(["POST"])
def product_image_delete(request, pk):
    """Supprimer une image de produit (AJAX)"""
    try:
        image = get_object_or_404(ProductImage, pk=pk)
        product = image.product
        
        if image.is_primary and product.images.count() > 1:
            next_image = product.images.filter(is_primary=False).first()
            if next_image:
                next_image.is_primary = True
                next_image.save()
        
        image.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Image supprimée avec succès!'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur lors de la suppression: {str(e)}'
        })


@login_required
@user_passes_test(is_staff)
@require_http_methods(["POST"])
def product_toggle_status(request, pk):
    """Basculer le statut sold_out d'un produit (AJAX)"""
    try:
        product = get_object_or_404(Product, pk=pk)
        product.sold_out = not product.sold_out
        product.save()

        status = "épuisé" if product.sold_out else "disponible"

        return JsonResponse({
            'success': True,
            'message': f'Produit "{product.name}" marqué comme {status}!',
            'new_status': product.sold_out
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur: {str(e)}'
        })


# ======================== GESTION DES MESSAGES CONTACT ========================

@login_required
@user_passes_test(is_staff)
def contact_list(request):
    """Liste des messages de contact"""
    contacts = Contact.objects.all().order_by('-created_at')

    # Filtres
    status_filter = request.GET.get('status')
    if status_filter == 'unread':
        contacts = contacts.filter(is_read=False)
    elif status_filter == 'read':
        contacts = contacts.filter(is_read=True)

    # Recherche
    search_query = request.GET.get('q')
    if search_query:
        contacts = contacts.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(message__icontains=search_query)
        )

    # Statistiques
    total_contacts = Contact.objects.count()
    unread_count = Contact.objects.filter(is_read=False).count()
    read_count = Contact.objects.filter(is_read=True).count()

    # Pagination
    paginator = Paginator(contacts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'contacts': page_obj,
        'total_contacts': total_contacts,
        'unread_count': unread_count,
        'read_count': read_count,
        'current_status': status_filter,
        'search_query': search_query,
    }

    return render(request, 'shop/admin/contact_list.html', context)


@login_required
@user_passes_test(is_staff)
def contact_detail(request, pk):
    """Détail d'un message de contact"""
    contact = get_object_or_404(Contact, pk=pk)

    # Marquer comme lu automatiquement
    if not contact.is_read:
        contact.is_read = True
        contact.save()

    # Récupérer les messages précédents du même expéditeur
    previous_messages = Contact.objects.filter(
        email=contact.email
    ).exclude(pk=pk).order_by('-created_at')[:5]

    context = {
        'contact': contact,
        'previous_messages': previous_messages,
    }

    return render(request, 'shop/admin/contact_detail.html', context)


@login_required
@user_passes_test(is_staff)
@require_http_methods(["POST"])
def contact_toggle_read(request, pk):
    """Marquer un message comme lu/non lu (AJAX)"""
    try:
        contact = get_object_or_404(Contact, pk=pk)
        contact.is_read = not contact.is_read
        contact.save()

        status = "lu" if contact.is_read else "non lu"

        return JsonResponse({
            'success': True,
            'message': f'Message marqué comme {status}',
            'is_read': contact.is_read
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur: {str(e)}'
        })


@login_required
@user_passes_test(is_staff)
@require_http_methods(["POST"])
def contact_delete(request, pk):
    """Supprimer un message de contact"""
    try:
        contact = get_object_or_404(Contact, pk=pk)
        contact.delete()

        messages.success(request, 'Message supprimé avec succès!')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Message supprimé avec succès!'
            })
        else:
            return redirect('shop:contact_list')

    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': f'Erreur lors de la suppression: {str(e)}'
            })
        else:
            messages.error(request, f'Erreur lors de la suppression: {str(e)}')
            return redirect('shop:contact_list')


@login_required
@user_passes_test(is_staff)
@require_http_methods(["POST"])
def contact_mark_all_read(request):
    """Marquer tous les messages comme lus"""
    try:
        Contact.objects.filter(is_read=False).update(is_read=True)

        messages.success(request, 'Tous les messages ont été marqués comme lus!')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Tous les messages ont été marqués comme lus!'
            })
        else:
            return redirect('shop:contact_list')

    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': f'Erreur: {str(e)}'
            })
        else:
            messages.error(request, f'Erreur: {str(e)}')
            return redirect('shop:contact_list')
    


