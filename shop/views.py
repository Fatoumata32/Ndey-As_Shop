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
from django.views.decorators.http import require_http_methods, require_POST
from django.db.models import Q, Count, Sum, Avg
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
import json
import logging
import urllib.parse

from .models import Product, Category, Cart, CartItem, Order, OrderItem, Contact, ProductImage, Size, ProductReview
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

    # Filtre de prix
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    if min_price:
        try:
            min_price = float(min_price)
            products = products.filter(price__gte=min_price)
        except (ValueError, TypeError):
            pass

    if max_price:
        try:
            max_price = float(max_price)
            products = products.filter(price__lte=max_price)
        except (ValueError, TypeError):
            pass

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

    # Pagination - 12 produits par page
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # Récupérer les favoris de l'utilisateur si connecté
    user_favorites = []
    if request.user.is_authenticated:
        from shop.models import Favorite
        user_favorites = list(Favorite.objects.filter(user=request.user).values_list('product_id', flat=True))

    context = {
        'products': page_obj,
        'page_obj': page_obj,
        'categories': categories,
        'current_category': category_filter,
        'search_query': search_query,
        'current_sort': sort,
        'user_favorites': user_favorites,
    }
    return render(request, 'shop/shop.html', context)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

def product_detail(request, product_id):
    """Détail d'un produit"""
    try:
        # Fetch product by ID with optimized queries
        product = get_object_or_404(
            Product.objects.select_related('category').prefetch_related('images', 'sizes', 'reviews__user'),
            id=product_id
        )

        # Vérifier si le produit est épuisé
        if product.sold_out:
            messages.warning(request, f"Le produit '{product.name}' est actuellement épuisé.")

        # Récupérer des produits similaires avec optimisation
        related_products = Product.objects.filter(
            category=product.category,
            sold_out=False
        ).exclude(id=product.id).select_related('category').prefetch_related('images')[:4]

        # Vérifier si le produit est dans les favoris de l'utilisateur
        is_favorited = False
        if request.user.is_authenticated:
            from shop.models import Favorite
            is_favorited = Favorite.objects.filter(user=request.user, product=product).exists()

        context = {
            'product': product,
            'related_products': related_products,
            'is_favorited': is_favorited,
        }
        return render(request, 'shop/item.html', context)
        
    except Product.DoesNotExist:
        logger.warning(f"Product with ID {product_id} does not exist")
        messages.error(request, "Le produit demandé n'existe pas.")
        return redirect('shop:shop')
    except Exception as e:
        logger.error(f"Error loading product {product_id}: {type(e).__name__}: {str(e)}", exc_info=True)
        messages.error(request, "Une erreur est survenue lors du chargement du produit.")
        return redirect('shop:shop')

def cart_view(request):
    """Vue du panier"""
    cart = get_or_create_cart(request)
    # Optimiser les requêtes pour les items du panier
    cart.items.all().select_related('product__category').prefetch_related('product__images')
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

            # Vérifier si le produit a des tailles et qu'une taille est sélectionnée
            if product.sizes.exists() and not selected_size:
                return JsonResponse({
                    'success': False,
                    'message': 'Veuillez sélectionner une taille pour ce produit.'
                })

            # Obtenir ou créer l'article du panier avec selected_size toujours défini
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                selected_size=selected_size or '',  # S'assurer que ce n'est jamais None
                defaults={'quantity': quantity}
            )

            if not created:
                cart_item.quantity += quantity
                cart_item.save()
            
            # Calculate total quantity in cart
            total_quantity = sum(item.quantity for item in cart.items.all())

            return JsonResponse({
                'success': True,
                'message': 'Produit ajouté au panier!',
                'cart_count': total_quantity
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
            cart_item.quantity = quantity
            cart_item.save()

        cart = get_or_create_cart(request)
        return JsonResponse({
            'success': True,
            'cart_total': str(cart.get_total()),
            'cart_count': sum(item.quantity for item in cart.items.all())
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
            'cart_count': sum(item.quantity for item in cart.items.all())
        })


def get_cart_count(request):
    """Obtenir le nombre d'articles dans le panier (AJAX)"""
    cart = get_or_create_cart(request)
    count = sum(item.quantity for item in cart.items.all())
    return JsonResponse({
        'success': True,
        'count': count
    })


def clear_whatsapp_session(request):
    """Nettoyer les données WhatsApp de la session"""
    if 'whatsapp_url' in request.session:
        del request.session['whatsapp_url']
    if 'order_id' in request.session:
        del request.session['order_id']
    return JsonResponse({'success': True})


def checkout(request):
    """Page de commande améliorée"""
    cart = get_or_create_cart(request)

    # Optimiser les requêtes pour les items du panier
    cart_items = cart.items.select_related('product__category').prefetch_related('product__images').all()

    # Vérifier si le panier est vide
    if not cart_items.exists():
        messages.warning(request, 'Votre panier est vide.')
        return redirect('shop:cart')

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Récupérer les données du formulaire
                customer_name = request.POST.get('customer_name', '')
                customer_email = request.POST.get('customer_email', '')
                customer_phone = request.POST.get('customer_phone', '')
                customer_address = request.POST.get('customer_address', '').strip()  # Strip whitespace and allow empty
                payment_method = request.POST.get('payment_method', 'cash')
                delivery_option = request.POST.get('delivery_option', 'standard')
                notes = request.POST.get('notes', '')

                # Utiliser les infos de l'utilisateur connecté si disponibles
                if request.user.is_authenticated:
                    if not customer_name:
                        customer_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
                    if not customer_email:
                        customer_email = request.user.email

                # Validation des données (ONLY name + phone are required, address is optional)
                if not customer_name or not customer_phone:
                    messages.error(request, 'Veuillez remplir tous les champs obligatoires.')
                    # CRITICAL: Preserve cart data on validation error
                    context = {
                        'cart': cart,
                        'cart_items': cart.items.all(),
                        'total': cart.get_total(),
                    }
                    return render(request, 'shop/checkout.html', context)

                # Normalize payment_method (replace hyphens with underscores for database storage)
                payment_method_normalized = payment_method.replace('-', '_')

                # Créer la commande
                order = Order.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    customer_name=customer_name,
                    customer_email=customer_email,
                    customer_phone=customer_phone,
                    customer_address=customer_address,
                    payment_method=payment_method_normalized,
                    total_amount=cart.get_total(),
                    status='pending'
                )

                # Créer les articles de commande
                for cart_item in cart.items.all():
                    OrderItem.objects.create(
                        order=order,
                        product=cart_item.product,
                        quantity=cart_item.quantity,
                        price=cart_item.product.get_current_price(),
                        selected_size=cart_item.selected_size or ''
                    )

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

                # Préparer le message WhatsApp avec formatage amélioré
                from datetime import datetime
                current_date = datetime.now().strftime("%d/%m/%Y")
                current_time = datetime.now().strftime("%H:%M")

                # Déterminer le mode de paiement avec emoji (using normalized method)
                if payment_method_normalized == 'cash':
                    payment_display = '💵 Paiement à la livraison'
                elif payment_method_normalized == 'wave':
                    payment_display = '📱 Wave'
                else:  # orange_money
                    payment_display = '📱 Orange Money'

                # Déterminer le type de livraison
                delivery_type = '📦 Standard (2-3 jours)'  # Par défaut standard car option express supprimée

                # Build address section: only include if address is not empty
                address_section = f"• *Adresse:* {customer_address}" if customer_address else "• *Adresse:* Non fournie"

                whatsapp_message = f"""🛍️ *NOUVELLE COMMANDE - NDEY'AS SHOP*
══════════════════════════════

📅 *Date:* {current_date}
⏰ *Heure:* {current_time}
🔢 *Commande N°:* {order.id}

👤 *INFORMATIONS CLIENT*
───────────────────────
• *Nom:* {customer_name}
• *Téléphone:* +221 {customer_phone}
• *Email:* {customer_email if customer_email else 'Non fourni'}

🚚 *LIVRAISON*
───────────────────────
{address_section}
• *Type:* {delivery_type}

🛒 *ARTICLES COMMANDÉS*
───────────────────────"""

                for item in order.items.all():
                    whatsapp_message += f"\n• *{item.product.name}*"
                    whatsapp_message += f"\n  └ Quantité: {item.quantity}"
                    if item.selected_size:
                        whatsapp_message += f" | Taille: {item.selected_size}"
                    whatsapp_message += f"\n  └ Prix: {item.get_subtotal()} FCFA"

                whatsapp_message += f"""

══════════════════════════════
💰 *TOTAL: {order.total_amount} FCFA*
══════════════════════════════

💳 *MODE DE PAIEMENT:* {payment_display}"""

                if notes:
                    whatsapp_message += f"\n📝 *Notes:* {notes}"

                whatsapp_message += "\n\n✨ Merci pour votre commande!"

                # Générer le lien WhatsApp avec l'API correcte
                import urllib.parse
                whatsapp_number = "221775457482"  # Numéro WhatsApp NDEY'AS SHOP
                # Utiliser l'API WhatsApp directe pour ouvrir l'app
                encoded_message = urllib.parse.quote(whatsapp_message)
                whatsapp_url = f"https://api.whatsapp.com/send/?phone={whatsapp_number}&text={encoded_message}&type=phone_number&app_absent=0"

                # Stocker le lien dans la session pour l'afficher après redirection
                request.session['whatsapp_url'] = whatsapp_url
                request.session['order_id'] = order.id

                messages.success(request, f'Commande #{order.id} passée avec succès!')

                # Créer une page de confirmation avec le lien WhatsApp
                return render(request, 'shop/order_success.html', {
                    'order': order,
                    'whatsapp_url': whatsapp_url
                })

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


@login_required
@require_http_methods(["POST"])
def add_review(request, product_id):
    """Ajouter ou modifier un avis sur un produit (AJAX)"""
    try:
        product = get_object_or_404(Product, id=product_id)
        data = json.loads(request.body)
        rating = int(data.get('rating', 0))
        comment = data.get('comment', '')

        if not 1 <= rating <= 5:
            return JsonResponse({
                'success': False,
                'message': 'La note doit être entre 1 et 5'
            })

        review, created = ProductReview.objects.update_or_create(
            product=product,
            user=request.user,
            defaults={
                'rating': rating,
                'comment': comment
            }
        )

        average_rating = product.get_average_rating()
        total_reviews = product.get_rating_count()

        return JsonResponse({
            'success': True,
            'message': 'Votre avis a été enregistré avec succès!',
            'average_rating': round(average_rating, 1),
            'total_reviews': total_reviews,
            'created': created
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur: {str(e)}'
        })


@login_required
@require_http_methods(["DELETE"])
def delete_review(request, product_id):
    """Supprimer son avis sur un produit (AJAX)"""
    try:
        product = get_object_or_404(Product, id=product_id)
        review = get_object_or_404(ProductReview, product=product, user=request.user)
        review.delete()

        average_rating = product.get_average_rating()
        total_reviews = product.get_rating_count()

        return JsonResponse({
            'success': True,
            'message': 'Votre avis a été supprimé',
            'average_rating': round(average_rating, 1),
            'total_reviews': total_reviews
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur: {str(e)}'
        })


def get_product_reviews(request, product_id):
    """Récupérer les avis d'un produit (AJAX)"""
    try:
        product = get_object_or_404(Product, id=product_id)
        reviews = product.reviews.select_related('user').order_by('-created_at')

        page = request.GET.get('page', 1)
        paginator = Paginator(reviews, 5)

        try:
            reviews_page = paginator.page(page)
        except PageNotAnInteger:
            reviews_page = paginator.page(1)
        except EmptyPage:
            reviews_page = paginator.page(paginator.num_pages)

        reviews_data = []
        for review in reviews_page:
            reviews_data.append({
                'id': review.id,
                'user': review.user.username,
                'rating': review.rating,
                'comment': review.comment,
                'date': review.created_at.strftime('%d/%m/%Y'),
                'is_owner': review.user == request.user if request.user.is_authenticated else False
            })

        return JsonResponse({
            'success': True,
            'reviews': reviews_data,
            'has_next': reviews_page.has_next(),
            'has_previous': reviews_page.has_previous(),
            'current_page': reviews_page.number,
            'total_pages': paginator.num_pages,
            'average_rating': round(product.get_average_rating(), 1),
            'total_reviews': product.get_rating_count(),
            'rating_distribution': product.get_rating_distribution()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur: {str(e)}'
        })


# ======================== VUES AUTHENTIFICATION ========================

def login_register_view(request):
    """Vue pour afficher la page de connexion/inscription"""
    if request.user.is_authenticated:
        return redirect('shop:index')
    return render(request, 'shop/login.html')


@ensure_csrf_cookie
def ajax_login(request):
    """Vue AJAX pour la connexion"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            password = data.get('password')

            if not email or not password:
                return JsonResponse({
                    'success': False,
                    'message': 'Email et mot de passe requis!'
                })

            # Chercher l'utilisateur par email
            try:
                user = User.objects.get(email=email)
                # Authentifier avec le username
                authenticated_user = authenticate(request, username=user.username, password=password)

                if authenticated_user is not None:
                    login(request, authenticated_user)
                    return JsonResponse({
                        'success': True,
                        'message': 'Connexion réussie!',
                        'redirect_url': '/'
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
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Données invalides!'
            })
        except Exception as e:
            logger.error(f"Erreur login: {e}")
            return JsonResponse({
                'success': False,
                'message': 'Une erreur est survenue lors de la connexion.'
            })

    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})


@ensure_csrf_cookie
def ajax_register(request):
    """Vue AJAX pour l'inscription"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
            confirm_password = data.get('confirm_password')

            # Validation des champs requis
            if not username or not email or not password:
                return JsonResponse({
                    'success': False,
                    'message': 'Nom d\'utilisateur, email et mot de passe sont requis!'
                })

            # Vérification de la correspondance des mots de passe
            if password != confirm_password:
                return JsonResponse({
                    'success': False,
                    'message': 'Les mots de passe ne correspondent pas!'
                })

            # Validation de la longueur du mot de passe
            if len(password) < 8:
                return JsonResponse({
                    'success': False,
                    'message': 'Le mot de passe doit contenir au moins 8 caractères!'
                })

            # Vérifier si l'email existe déjà
            if User.objects.filter(email=email).exists():
                return JsonResponse({
                    'success': False,
                    'message': 'Un compte existe déjà avec cet email!'
                })

            # Vérifier si le nom d'utilisateur existe déjà
            if User.objects.filter(username=username).exists():
                return JsonResponse({
                    'success': False,
                    'message': 'Ce nom d\'utilisateur est déjà pris!'
                })

            # Créer l'utilisateur
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )

            # Connecter automatiquement l'utilisateur après inscription avec le backend Django
            from django.contrib.auth import authenticate
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)

            return JsonResponse({
                'success': True,
                'message': 'Inscription réussie!',
                'redirect_url': '/'
            })

        except json.JSONDecodeError as e:
            logger.error(f"JSONDecodeError lors de l'inscription: {e}")
            logger.error(f"Body reçu: {request.body}")
            return JsonResponse({
                'success': False,
                'message': 'Données invalides! Veuillez réessayer.'
            })
        except Exception as e:
            logger.error(f"Erreur inscription: {e}")
            logger.error(f"Type d'erreur: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return JsonResponse({
                'success': False,
                'message': f'Une erreur est survenue: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})


def logout_view(request):
    """Vue pour la déconnexion"""
    logout(request)
    messages.success(request, 'Vous avez été déconnecté avec succès!')
    return redirect('shop:login')


@ensure_csrf_cookie
def forgot_password(request):
    """Vue pour demander la réinitialisation du mot de passe"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')

            if not email:
                return JsonResponse({
                    'success': False,
                    'message': 'Veuillez entrer votre email!'
                })

            try:
                user = User.objects.get(email=email)
                # Générer un token de réinitialisation (simplifié pour la démo)
                from django.utils.crypto import get_random_string
                token = get_random_string(32)

                # Stocker le token dans la session (pour la démo)
                request.session[f'reset_token_{token}'] = {
                    'user_id': user.id,
                    'timestamp': str(timezone.now())
                }

                # Dans un cas réel, envoyer un email avec le lien
                reset_link = f"{request.build_absolute_uri('/shop/reset-password/')}?token={token}"

                # Pour la démo, on retourne juste un message de succès
                logger.info(f"Reset link for {email}: {reset_link}")

                return JsonResponse({
                    'success': True,
                    'message': f'Un lien de réinitialisation a été envoyé à {email}',
                    'demo_token': token  # Pour la démo uniquement
                })

            except User.DoesNotExist:
                # Par sécurité, on ne révèle pas si l'email existe ou non
                return JsonResponse({
                    'success': True,
                    'message': f'Si un compte existe avec {email}, un lien de réinitialisation sera envoyé.'
                })

        except Exception as e:
            logger.error(f"Erreur forgot password: {e}")
            return JsonResponse({
                'success': False,
                'message': 'Une erreur est survenue.'
            })

    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})


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
    orders = Order.objects.filter(user=request.user).prefetch_related('items__product__images').order_by('-created_at')

    # Filtrage par statut si spécifié
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)

    # Pagination
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'orders': page_obj,
        'page_obj': page_obj,
    }
    return render(request, 'shop/user_orders.html', context)


def favorites(request):
    """Vue pour afficher les produits favoris"""
    # Récupérer les favoris depuis la session
    favorites_list = request.session.get('favorites', [])
    products = Product.objects.filter(id__in=favorites_list)

    context = {
        'products': products,
        'favorites_list': favorites_list,
    }
    return render(request, 'shop/favorites.html', context)


@require_POST
def toggle_favorite(request):
    """AJAX: Ajouter ou retirer un produit des favoris"""
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')

        if not product_id:
            return JsonResponse({'success': False, 'message': 'ID produit requis'})

        # Récupérer les favoris de la session
        favorites = request.session.get('favorites', [])

        if product_id in favorites:
            # Retirer des favoris
            favorites.remove(product_id)
            is_favorite = False
            message = 'Retiré des favoris'
        else:
            # Ajouter aux favoris
            favorites.append(product_id)
            is_favorite = True
            message = 'Ajouté aux favoris'

        # Sauvegarder dans la session
        request.session['favorites'] = favorites
        request.session.modified = True

        return JsonResponse({
            'success': True,
            'is_favorite': is_favorite,
            'message': message,
            'favorites_count': len(favorites)
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def user_order_detail(request, order_id):
    """Vue pour afficher les détails d'une commande pour l'utilisateur"""
    # Vérifier que la commande appartient bien à l'utilisateur connecté
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Vérifier si la commande peut être annulée ou modifiée
    can_cancel = order.status in ['pending', 'confirmed']
    can_modify = order.status in ['pending']

    context = {
        'order': order,
        'can_cancel': can_cancel,
        'can_modify': can_modify,
    }
    return render(request, 'shop/user_order_detail.html', context)


@login_required
@require_POST
def cancel_order(request, order_id):
    """Annuler une commande avec notification WhatsApp"""
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)

        # Vérifier si la commande peut être annulée
        if order.status not in ['pending', 'confirmed']:
            return JsonResponse({
                'success': False,
                'message': 'Cette commande ne peut plus être annulée.'
            })

        # Mettre à jour le statut de la commande
        order.status = 'cancelled'
        order.save()

        # Préparer le message WhatsApp
        message = f"""🚫 *ANNULATION DE COMMANDE*

Commande #{order.id} a été annulée

*Client:* {order.name}
*Téléphone:* {order.phone}
*Date:* {order.created_at.strftime('%d/%m/%Y à %H:%M')}
*Montant:* {order.total_amount} FCFA

*Raison:* Annulation par le client

---
NDEY'AS SHOP"""

        # Envoyer notification WhatsApp au vendeur
        whatsapp_url = f"https://api.whatsapp.com/send?phone=221775457482&text={urllib.parse.quote(message)}"

        return JsonResponse({
            'success': True,
            'message': 'Votre commande a été annulée avec succès.',
            'whatsapp_url': whatsapp_url
        })

    except Exception as e:
        logger.error(f"Erreur lors de l'annulation de la commande: {e}")
        return JsonResponse({
            'success': False,
            'message': 'Une erreur est survenue lors de l\'annulation.'
        })


@login_required
@require_POST
def modify_order(request, order_id):
    """Renvoyer/Modifier une commande avec notification WhatsApp"""
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)

        # Vérifier si la commande peut être modifiée
        if order.status != 'pending':
            return JsonResponse({
                'success': False,
                'message': 'Cette commande ne peut plus être modifiée.'
            })

        # Récupérer les modifications
        data = json.loads(request.body)
        modification_reason = data.get('reason', 'Modification demandée par le client')

        # Préparer le message WhatsApp avec les détails de modification
        items_detail = "\n".join([
            f"- {item.product.name} (Qté: {item.quantity}, Taille: {item.selected_size or 'N/A'})"
            for item in order.items.all()
        ])

        message = f"""✏️ *DEMANDE DE MODIFICATION*

Commande #{order.id}

*Client:* {order.name}
*Téléphone:* {order.phone}
*Email:* {order.email or 'Non fourni'}
*Date commande:* {order.created_at.strftime('%d/%m/%Y à %H:%M')}

*Articles actuels:*
{items_detail}

*Montant:* {order.total_amount} FCFA

*Raison de modification:*
{modification_reason}

*Action requise:* Veuillez contacter le client pour finaliser les modifications.

---
NDEY'AS SHOP"""

        # Envoyer notification WhatsApp au vendeur
        whatsapp_url = f"https://api.whatsapp.com/send?phone=221775457482&text={urllib.parse.quote(message)}"

        # Marquer la commande comme en cours de modification
        order.notes = f"Modification demandée le {timezone.now().strftime('%d/%m/%Y à %H:%M')}: {modification_reason}\n{order.notes or ''}"
        order.save()

        return JsonResponse({
            'success': True,
            'message': 'Votre demande de modification a été envoyée. Nous vous contacterons bientôt.',
            'whatsapp_url': whatsapp_url
        })

    except Exception as e:
        logger.error(f"Erreur lors de la modification de la commande: {e}")
        return JsonResponse({
            'success': False,
            'message': 'Une erreur est survenue lors de la modification.'
        })


@login_required
@require_POST
def reorder(request, order_id):
    """Commander à nouveau les articles d'une ancienne commande"""
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)

        # Récupérer ou créer le panier de l'utilisateur
        if request.user.is_authenticated:
            cart, created = Cart.objects.get_or_create(user=request.user)
        else:
            session_key = request.session.session_key
            if not session_key:
                request.session.create()
                session_key = request.session.session_key
            cart, created = Cart.objects.get_or_create(session_key=session_key)

        # Ajouter les articles de la commande au panier
        items_added = []
        for order_item in order.items.all():
            if order_item.product and not order_item.product.sold_out:
                cart_item, created = CartItem.objects.get_or_create(
                    cart=cart,
                    product=order_item.product,
                    selected_size=order_item.selected_size,
                    defaults={'quantity': order_item.quantity}
                )
                if not created:
                    cart_item.quantity += order_item.quantity
                    cart_item.save()
                items_added.append(order_item.product.name)

        if items_added:
            return JsonResponse({
                'success': True,
                'message': f'{len(items_added)} article(s) ajouté(s) au panier',
                'redirect_url': '/cart/'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Aucun article disponible pour une nouvelle commande'
            })

    except Exception as e:
        logger.error(f"Erreur lors de la nouvelle commande: {e}")
        return JsonResponse({
            'success': False,
            'message': 'Une erreur est survenue'
        })


@login_required
def track_order(request, order_id):
    """Suivre une commande en livraison"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Pour l'instant, on redirige vers la page de détail
    # Plus tard, on pourra intégrer un vrai système de tracking
    return redirect('shop:user_order_detail', order_id=order_id)


@login_required
def review_order(request, order_id):
    """Page pour évaluer les produits d'une commande livrée"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status != 'delivered':
        messages.error(request, "Vous ne pouvez évaluer que les commandes livrées.")
        return redirect('shop:user_orders')

    # Pour l'instant, on redirige vers la page de détail
    # où l'utilisateur peut voir les produits et les évaluer
    return redirect('shop:user_order_detail', order_id=order_id)


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
    
    # Pagination
    paginator = Paginator(products, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.all()

    # Calculate statistics from all products (not just current page)
    all_products = Product.objects.all()
    stats = {
        'total_products': all_products.count(),
        'available_products': all_products.filter(sold_out=False).count(),
        'on_sale_products': all_products.filter(on_sale=True).count(),
        'sold_out_products': all_products.filter(sold_out=True).count(),
    }

    context = {
        'page_obj': page_obj,
        'products': page_obj,
        'categories': categories,
        'current_category': category_filter,
        'search_query': search_query,
        'current_status': status_filter,
        'stats': stats,
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
            on_sale = request.POST.get('on_sale') == 'on'
            sold_out = request.POST.get('sold_out') == 'on'

            # Validation basique
            if not name or not category_id or not price:
                messages.error(request, 'Veuillez remplir tous les champs obligatoires (nom, catégorie, prix).')
                categories = Category.objects.all()
                recent_products = Product.objects.select_related('category').order_by('-created_at')[:5]
                context = {
                    'categories': categories,
                    'recent_products': recent_products,
                }
                return render(request, 'shop/admin/product_add.html', context)

            # Validation du prix
            try:
                price_float = float(price)
                if price_float <= 0:
                    raise ValueError("Le prix doit être supérieur à 0")
            except ValueError as e:
                messages.error(request, f'Prix invalide: {str(e)}')
                categories = Category.objects.all()
                recent_products = Product.objects.select_related('category').order_by('-created_at')[:5]
                context = {
                    'categories': categories,
                    'recent_products': recent_products,
                }
                return render(request, 'shop/admin/product_add.html', context)

            # Validation du prix de vente
            sale_price_float = None
            if sale_price:
                try:
                    sale_price_float = float(sale_price)
                    if sale_price_float <= 0:
                        raise ValueError("Le prix de vente doit être supérieur à 0")
                    if sale_price_float >= price_float:
                        raise ValueError("Le prix de vente doit être inférieur au prix normal")
                except ValueError as e:
                    messages.error(request, f'Prix de vente invalide: {str(e)}')
                    categories = Category.objects.all()
                    recent_products = Product.objects.select_related('category').order_by('-created_at')[:5]
                    context = {
                        'categories': categories,
                        'recent_products': recent_products,
                    }
                    return render(request, 'shop/admin/product_add.html', context)
            elif on_sale:
                # If on_sale is True, sale_price is required
                messages.error(request, 'Le prix de promotion est obligatoire lorsque le produit est en promotion.')
                categories = Category.objects.all()
                recent_products = Product.objects.select_related('category').order_by('-created_at')[:5]
                context = {
                    'categories': categories,
                    'recent_products': recent_products,
                }
                return render(request, 'shop/admin/product_add.html', context)

            # Vérifier que la catégorie existe
            try:
                category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                messages.error(request, 'La catégorie sélectionnée n\'existe pas.')
                categories = Category.objects.all()
                recent_products = Product.objects.select_related('category').order_by('-created_at')[:5]
                context = {
                    'categories': categories,
                    'recent_products': recent_products,
                }
                return render(request, 'shop/admin/product_add.html', context)

            # Créer le produit
            with transaction.atomic():
                product = Product.objects.create(
                    name=name,
                    description=description or '',
                    category=category,
                    price=price_float,
                    sale_price=sale_price_float,
                    on_sale=on_sale,
                    sold_out=sold_out
                )

                # Gestion des tailles
                size_ids = request.POST.getlist('sizes')
                if size_ids:
                    for size_id in size_ids:
                        try:
                            size = Size.objects.get(id=size_id)
                            product.sizes.add(size)
                        except Size.DoesNotExist:
                            logger.warning(f"Taille {size_id} non trouvée")
                            pass

                # Gestion des images multiples
                images = request.FILES.getlist('images')
                if images:
                    for i, image in enumerate(images):
                        try:
                            ProductImage.objects.create(
                                product=product,
                                image=image,
                                is_primary=(i == 0)
                            )
                        except Exception as e:
                            logger.error(f"Erreur lors de l'ajout de l'image {i}: {str(e)}")
                            # Continue avec les autres images même si une échoue

                messages.success(request, f'Produit "{product.name}" ajouté avec succès!')
                return redirect('shop:product_list')

        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du produit: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            messages.error(request, f'Erreur lors de l\'ajout du produit: {str(e)}')
            categories = Category.objects.all()
            recent_products = Product.objects.select_related('category').order_by('-created_at')[:5]
            context = {
                'categories': categories,
                'recent_products': recent_products,
            }
            return render(request, 'shop/admin/product_add.html', context)

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
def bulk_product_add(request):
    """Ajout intelligent de plusieurs produits en lot"""
    import json

    if request.method == 'POST':
        try:
            # Récupérer les données JSON des produits
            products_data = json.loads(request.POST.get('products_data', '[]'))

            if not products_data:
                messages.error(request, 'Aucun produit à ajouter.')
                return redirect('shop:bulk_product_add')

            created_products = []
            errors = []

            with transaction.atomic():
                for idx, product_data in enumerate(products_data):
                    try:
                        # Validation des champs obligatoires
                        name = product_data.get('name', '').strip()
                        category_id = product_data.get('category_id')
                        price = product_data.get('price')

                        if not name or not category_id or not price:
                            errors.append(f"Produit {idx + 1}: Champs obligatoires manquants (nom, catégorie, prix)")
                            continue

                        # Récupérer la catégorie
                        try:
                            category = Category.objects.get(id=category_id)
                        except Category.DoesNotExist:
                            errors.append(f"Produit {idx + 1} ({name}): Catégorie invalide")
                            continue

                        # Créer le produit
                        product = Product.objects.create(
                            name=name,
                            description=product_data.get('description', ''),
                            category=category,
                            price=float(price),
                            sale_price=float(product_data.get('sale_price')) if product_data.get('sale_price') else None,
                            on_sale=product_data.get('on_sale', False),
                            sold_out=product_data.get('sold_out', False)
                        )

                        # Ajouter les tailles
                        size_ids = product_data.get('sizes', [])
                        if size_ids:
                            for size_id in size_ids:
                                try:
                                    size = Size.objects.get(id=size_id)
                                    product.sizes.add(size)
                                except Size.DoesNotExist:
                                    pass

                        # Traiter les images associées
                        image_indices = product_data.get('image_indices', [])
                        if image_indices:
                            images = request.FILES.getlist('images')
                            for i, img_idx in enumerate(image_indices):
                                if 0 <= img_idx < len(images):
                                    try:
                                        ProductImage.objects.create(
                                            product=product,
                                            image=images[img_idx],
                                            is_primary=(i == 0),
                                            order=i
                                        )
                                    except Exception as e:
                                        logger.error(f"Erreur ajout image {img_idx} pour {name}: {str(e)}")

                        created_products.append(product.name)

                    except Exception as e:
                        errors.append(f"Produit {idx + 1}: {str(e)}")
                        logger.error(f"Erreur création produit {idx + 1}: {str(e)}")

            # Messages de résultat
            if created_products:
                messages.success(request, f'{len(created_products)} produit(s) créé(s) avec succès: {", ".join(created_products)}')

            if errors:
                for error in errors:
                    messages.warning(request, error)

            return redirect('shop:product_list')

        except Exception as e:
            logger.error(f"Erreur lors de l'ajout en lot: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            messages.error(request, f'Erreur lors de l\'ajout en lot: {str(e)}')

    # GET request
    categories = Category.objects.all().order_by('name')
    all_sizes = Size.objects.all().order_by('display_order', 'name')

    # Serialize data for JavaScript
    import json
    categories_json = json.dumps([
        {'id': cat.id, 'name': cat.name, 'icon': cat.icon if hasattr(cat, 'icon') else ''}
        for cat in categories
    ])
    sizes_json = json.dumps([
        {'id': size.id, 'name': size.name}
        for size in all_sizes
    ])

    context = {
        'categories': categories,
        'all_sizes': all_sizes,
        'categories_json': categories_json,
        'sizes_json': sizes_json,
        'recent_products': Product.objects.select_related('category').order_by('-created_at')[:5],
    }

    return render(request, 'shop/admin/bulk_product_add.html', context)


@login_required
@user_passes_test(is_staff)
def product_edit(request, pk):
    """Modifier un produit"""
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        try:
            # Récupération manuelle des données
            name = request.POST.get('name')
            description = request.POST.get('description')
            category_id = request.POST.get('category')
            price = request.POST.get('price')
            sale_price = request.POST.get('sale_price')
            on_sale = request.POST.get('on_sale') == 'on'
            sold_out = request.POST.get('sold_out') == 'on'

            # Validation basique
            if not name or not category_id or not price:
                messages.error(request, 'Veuillez remplir tous les champs obligatoires (nom, catégorie, prix).')
                context = {
                    'form': ProductForm(instance=product),
                    'product': product,
                    'existing_images': product.images.all(),
                }
                return render(request, 'shop/admin/product_edit.html', context)

            # Validation du prix
            try:
                price_float = float(price)
                if price_float <= 0:
                    raise ValueError("Le prix doit être supérieur à 0")
            except ValueError as e:
                messages.error(request, f'Prix invalide: {str(e)}')
                context = {
                    'form': ProductForm(instance=product),
                    'product': product,
                    'existing_images': product.images.all(),
                }
                return render(request, 'shop/admin/product_edit.html', context)

            # Validation du prix de vente
            sale_price_float = None
            if sale_price:
                try:
                    sale_price_float = float(sale_price)
                    if sale_price_float <= 0:
                        raise ValueError("Le prix de vente doit être supérieur à 0")
                    if sale_price_float >= price_float:
                        raise ValueError("Le prix de vente doit être inférieur au prix normal")
                except ValueError as e:
                    messages.error(request, f'Prix de vente invalide: {str(e)}')
                    context = {
                        'form': ProductForm(instance=product),
                        'product': product,
                        'existing_images': product.images.all(),
                    }
                    return render(request, 'shop/admin/product_edit.html', context)
            elif on_sale:
                # If on_sale is True, sale_price is required
                messages.error(request, 'Le prix de promotion est obligatoire lorsque le produit est en promotion.')
                context = {
                    'form': ProductForm(instance=product),
                    'product': product,
                    'existing_images': product.images.all(),
                }
                return render(request, 'shop/admin/product_edit.html', context)

            # Vérifier que la catégorie existe
            try:
                category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                messages.error(request, 'La catégorie sélectionnée n\'existe pas.')
                context = {
                    'form': ProductForm(instance=product),
                    'product': product,
                    'existing_images': product.images.all(),
                }
                return render(request, 'shop/admin/product_edit.html', context)

            # Modifier le produit
            with transaction.atomic():
                product.name = name
                product.description = description or ''
                product.category = category
                product.price = price_float
                product.sale_price = sale_price_float
                product.on_sale = on_sale
                product.sold_out = sold_out
                # The save() method will auto-generate/update the slug
                product.save()

                # Gestion des tailles
                product.sizes.clear()  # Effacer les anciennes tailles
                size_ids = request.POST.getlist('sizes')
                if size_ids:
                    for size_id in size_ids:
                        try:
                            size = Size.objects.get(id=size_id)
                            product.sizes.add(size)
                        except Size.DoesNotExist:
                            logger.warning(f"Taille {size_id} non trouvée")
                            pass

                # Gestion des nouvelles images
                new_images = request.FILES.getlist('images')
                if new_images:
                    for i, image in enumerate(new_images):
                        try:
                            # Si c'est la première image et qu'il n'y a pas d'images existantes
                            is_primary = (product.images.count() == 0 and i == 0)
                            ProductImage.objects.create(
                                product=product,
                                image=image,
                                is_primary=is_primary
                            )
                        except Exception as e:
                            logger.error(f"Erreur lors de l'ajout de l'image {i}: {str(e)}")
                            # Continue avec les autres images même si une échoue

                messages.success(request, f'Produit "{product.name}" modifié avec succès!')
                return redirect('shop:product_list')

        except Exception as e:
            logger.error(f"Erreur lors de la modification du produit: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            messages.error(request, f'Erreur lors de la modification: {str(e)}')
            context = {
                'form': ProductForm(instance=product),
                'product': product,
                'existing_images': product.images.all(),
            }
            return render(request, 'shop/admin/product_edit.html', context)

    # GET request
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
            category = form.save(commit=False)

            # Handle icon
            icon = request.POST.get('icon', '📦')
            category.icon = icon

            # Handle category_type
            category_type = request.POST.get('category_type', 'none')
            category.category_type = category_type

            category.save()

            # Handle available_sizes
            if category_type != 'none':
                selected_sizes = request.POST.getlist('available_sizes')
                if selected_sizes:
                    from shop.models import Size
                    # Create sizes if they don't exist and associate them
                    for size_name in selected_sizes:
                        size, created = Size.objects.get_or_create(name=size_name)
                        category.available_sizes.add(size)

            messages.success(request, f'Catégorie "{category.name}" ajoutée avec succès!')

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'category_id': category.id,
                    'category_name': category.name,
                    'category_icon': category.icon
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
        'categories': Category.objects.all().order_by('-created_at')[:5],
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
            category = form.save(commit=False)

            # Handle category_type
            category_type = request.POST.get('category_type', 'none')
            category.category_type = category_type

            category.save()

            # Handle available_sizes
            if category_type != 'none':
                selected_sizes = request.POST.getlist('available_sizes')
                if selected_sizes:
                    from shop.models import Size
                    sizes = Size.objects.filter(id__in=selected_sizes)
                    category.available_sizes.set(sizes)
                else:
                    category.available_sizes.clear()
            else:
                category.available_sizes.clear()

            messages.success(request, f'Catégorie "{category.name}" modifiée avec succès!')
            return redirect('shop:category_list')
        else:
            messages.error(request, 'Veuillez corriger les erreurs ci-dessous.')
    else:
        form = CategoryForm(instance=category)

    # Get all sizes for the template
    from shop.models import Size
    all_sizes = Size.objects.all().order_by('name')

    context = {
        'form': form,
        'category': category,
        'all_sizes': all_sizes,
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
def delete_order_history(request):
    """Supprimer l'historique des commandes terminées (livrées, annulées, en attente et en traitement)"""
    if request.method == 'POST':
        try:
            # Supprimer les commandes livrées, annulées, en attente et en traitement
            deleted_orders = Order.objects.filter(
                status__in=['pending', 'processing', 'delivered', 'cancelled']
            )
            deleted_count = deleted_orders.count()
            deleted_orders.delete()

            return JsonResponse({
                'success': True,
                'deleted_count': deleted_count,
                'message': f'{deleted_count} commande(s) supprimée(s) avec succès'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)

    return JsonResponse({
        'success': False,
        'message': 'Méthode non autorisée'
    }, status=405)


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
    from datetime import datetime
    today = datetime.now().date()

    total_contacts = Contact.objects.count()
    unread_count = Contact.objects.filter(is_read=False).count()
    read_count = Contact.objects.filter(is_read=True).count()
    today_count = Contact.objects.filter(created_at__date=today).count()

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
        'today_count': today_count,
        'status_filter': status_filter,
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


def get_product_sizes(request, product_id):
    """AJAX endpoint pour récupérer les tailles d'un produit"""
    try:
        product = get_object_or_404(Product, pk=product_id)
        sizes = []

        # Récupérer les tailles disponibles pour ce produit
        if product.sizes.exists():
            sizes = list(product.sizes.values_list('name', flat=True))

        return JsonResponse({
            'success': True,
            'sizes': sizes,
            'product_name': product.name,
            'category_type': product.category.category_type if product.category else 'none'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })


def get_category_sizes(request, category_id):
    """AJAX endpoint pour récupérer les tailles disponibles d'une catégorie"""
    try:
        category = get_object_or_404(Category, pk=category_id)
        sizes_data = []

        # Récupérer les tailles disponibles pour cette catégorie
        if category.available_sizes.exists():
            for size in category.available_sizes.all():
                sizes_data.append({
                    'id': size.id,
                    'name': size.name,
                    'size_type': size.size_type,
                    'display_order': size.display_order
                })

        return JsonResponse({
            'success': True,
            'sizes': sizes_data,
            'category_name': category.name,
            'category_type': category.category_type,
            'size_label': category.get_size_label()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@login_required
def favorites(request):
    """Afficher les produits favoris de l'utilisateur"""
    from shop.models import Favorite
    favorites = Favorite.objects.filter(user=request.user)
    return render(request, 'shop/favorites.html', {
        'favorites': favorites,
        'title': 'Mes Favoris'
    })


@login_required
@require_http_methods(["POST"])
def toggle_favorite(request):
    """Ajouter ou retirer un produit des favoris"""
    from shop.models import Favorite
    try:
        product_id = request.POST.get('product_id')
        if not product_id:
            return JsonResponse({'success': False, 'message': 'ID du produit manquant'})

        product = get_object_or_404(Product, pk=product_id)
        favorite, created = Favorite.objects.get_or_create(
            user=request.user,
            product=product
        )

        if not created:
            # Si le favori existe déjà, on le supprime
            favorite.delete()
            is_favorited = False
            message = 'Produit retiré des favoris'
        else:
            # Sinon on l'a créé
            is_favorited = True
            message = 'Produit ajouté aux favoris'

        # Compter le nombre total de favoris pour ce produit
        favorites_count = Favorite.objects.filter(product=product).count()

        return JsonResponse({
            'success': True,
            'is_favorited': is_favorited,
            'favorites_count': favorites_count,
            'message': message
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

