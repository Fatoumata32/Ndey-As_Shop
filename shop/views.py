from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from .models import Product, Category, Cart, CartItem, Order, OrderItem, Contact
from django.contrib.auth.models import User
import json

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

def index(request):
    """Page d'accueil (maintenant /home/)"""
    # Rediriger vers login si non authentifié
    if not request.user.is_authenticated:
        return redirect('shop:login')
    
    products = Product.objects.filter(sold_out=False)[:6]  # 6 derniers produits
    categories = Category.objects.all()
    context = {
        'products': products,
        'categories': categories,
    }
    return render(request, 'shop/index.html', context)




def shop(request):
    """Page boutique avec tous les produits"""
    # Rediriger vers login si non authentifié
    if not request.user.is_authenticated:
        return redirect('shop:login')
        
    products = Product.objects.all()
    categories = Category.objects.all()
    
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
    
    context = {
        'products': products,
        'categories': categories,
        'current_category': category_filter,
        'search_query': search_query,
    }
    return render(request, 'shop/shop.html', context)

def product_detail(request, product_id):
    """Détail d'un produit"""
    # Rediriger vers login si non authentifié
    if not request.user.is_authenticated:
        return redirect('shop:login')
        
    product = get_object_or_404(Product, id=product_id)
    context = {
        'product': product,
    }
    return render(request, 'shop/item.html', context)

def cart_view(request):
    """Vue du panier"""
    # Rediriger vers login si non authentifié
    if not request.user.is_authenticated:
        return redirect('shop:login')
        
    cart = get_or_create_cart(request)
    context = {
        'cart': cart,
    }
    return render(request, 'shop/cart.html', context)

@csrf_exempt
def add_to_cart(request):
    """Ajouter au panier (AJAX)"""
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'message': 'Vous devez être connecté pour ajouter au panier.',
            'redirect_url': '/'
        })
        
    if request.method == 'POST':
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)
        selected_size = data.get('selected_size', '')
        
        product = get_object_or_404(Product, id=product_id)
        cart = get_or_create_cart(request)
        
        # Vérifier le stock
        if product.quantity < quantity:
            return JsonResponse({
                'success': False,
                'message': f'Stock insuffisant! Seulement {product.quantity} unités disponibles.'
            })
        
        # Obtenir ou créer l'article du panier
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            selected_size=selected_size,
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

@csrf_exempt
def update_cart_item(request):
    """Mettre à jour la quantité d'un article (AJAX)"""
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'message': 'Vous devez être connecté.',
            'redirect_url': '/'
        })
        
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
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'message': 'Vous devez être connecté.',
            'redirect_url': '/'
        })
        
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
    """Page de commande"""
    # Rediriger vers login si non authentifié
    if not request.user.is_authenticated:
        return redirect('shop:login')
        
    cart = get_or_create_cart(request)
    
    if request.method == 'POST':
        # Créer la commande
        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            customer_name=request.POST.get('customer_name'),
            customer_phone=request.POST.get('customer_phone'),
            customer_address=request.POST.get('customer_address'),
            payment_method=request.POST.get('payment_method'),
            total_amount=cart.get_total()
        )
        
        # Créer les articles de commande et mettre à jour le stock
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.get_current_price(),
                selected_size=cart_item.selected_size
            )
            
            # Mettre à jour le stock du produit
            cart_item.product.quantity -= cart_item.quantity
            cart_item.product.save()
        
        # Vider le panier
        cart.items.all().delete()
        
        messages.success(request, 'Commande passée avec succès!')
        return redirect('shop:index')  # Redirige vers /home/
    
    context = {
        'cart': cart,
    }
    return render(request, 'shop/checkout.html', context)

def contact_view(request):
    """Page de contact"""
    # Rediriger vers login si non authentifié
    if not request.user.is_authenticated:
        return redirect('shop:login')
        
    if request.method == 'POST':
        Contact.objects.create(
            name=request.POST.get('name'),
            phone=request.POST.get('phone', ''),
            message=request.POST.get('message')
        )
        messages.success(request, 'Message envoyé avec succès!')
        return redirect('shop:contact')
    
    return render(request, 'shop/contact.html')

def login_register_view(request):
    """Vue pour afficher la page de connexion/inscription"""
    if request.user.is_authenticated:
        return redirect('shop:index')  # Rediriger vers /home/ si déjà connecté
    return render(request, 'shop/login.html')

@csrf_exempt
def ajax_login(request):
    """Vue AJAX pour la connexion"""
    if request.method == 'POST':
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')
        
        # Authentification par email
        try:
            user = User.objects.get(email=email)
            user = authenticate(request, username=user.username, password=password)
            
            if user is not None:
                login(request, user)
                return JsonResponse({
                    'success': True,
                    'message': 'Connexion réussie!',
                    'redirect_url': '/home/'  # Redirige vers la page d'accueil après connexion
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
        
        # Validation
        if password != confirm_password:
            return JsonResponse({
                'success': False,
                'message': 'Les mots de passe ne correspondent pas!'
            })
        
        # Vérifier si l'email existe déjà
        if User.objects.filter(email=email).exists():
            return JsonResponse({
                'success': False,
                'message': 'Un compte existe déjà avec cet email!'
            })
        
        try:
            # Créer l'utilisateur
            username = email.split('@')[0]  # Utiliser la partie avant @ comme username
            # S'assurer que le username est unique
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
            
            # Connecter automatiquement l'utilisateur après l'inscription
            login(request, user)
            
            return JsonResponse({
                'success': True,
                'message': 'Inscription réussie!',
                'redirect_url': '/home/'  # Redirige vers la page d'accueil après inscription
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
    return redirect('shop:login')  # Redirige vers la page de login

@csrf_exempt
def reset_password(request):
    """Vue pour réinitialiser le mot de passe"""
    if request.method == 'POST':
        data = json.loads(request.body)
        email = data.get('email')
        
        try:
            user = User.objects.get(email=email)
            # Ici, vous pouvez implémenter la logique d'envoi d'email
            # Pour l'instant, on retourne juste un message de succès
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

@login_required
def admin_dashboard(request):
    """Dashboard admin personnalisé"""
    if not request.user.is_staff:
        messages.error(request, 'Accès non autorisé.')
        return redirect('shop:index')  # Redirige vers /home/
    
    products = Product.objects.all()
    categories = Category.objects.all()
    orders = Order.objects.all()[:10]  # 10 dernières commandes
    
    context = {
        'products': products,
        'categories': categories,
        'orders': orders,
    }
    return render(request, 'shop/admin.html', context)

# Supprimer les vieilles vues login_view et register_view car elles sont remplacées

# shop/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.core.files.base import ContentFile
from .models import Product, Category, Cart, CartItem, Order, OrderItem, Contact, ProductImage
import json
import base64

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

@login_required
def index(request):
    """Page d'accueil"""
    products = Product.objects.filter(sold_out=False)[:6]  # 6 derniers produits
    categories = Category.objects.all()
    context = {
        'products': products,
        'categories': categories,
    }
    return render(request, 'shop/index.html', context)

@login_required
def shop(request):
    """Page boutique avec tous les produits"""
    products = Product.objects.all()
    categories = Category.objects.all()
    
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

@login_required
def product_detail(request, product_id):
    """Détail d'un produit"""
    product = get_object_or_404(Product, id=product_id)
    context = {
        'product': product,
    }
    return render(request, 'shop/item.html', context)

@login_required
def cart_view(request):
    """Vue du panier"""
    cart = get_or_create_cart(request)
    context = {
        'cart': cart,
    }
    return render(request, 'shop/cart.html', context)

@csrf_exempt
@login_required
def add_to_cart(request):
    """Ajouter au panier (AJAX)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            quantity = data.get('quantity', 1)
            selected_size = data.get('selected_size', '')
            
            product = get_object_or_404(Product, id=product_id)
            cart = get_or_create_cart(request)
            
            # Vérifier le stock
            if product.quantity < quantity:
                return JsonResponse({
                    'success': False,
                    'message': f'Stock insuffisant! Seulement {product.quantity} unités disponibles.'
                })
            
            # Obtenir ou créer l'article du panier
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                selected_size=selected_size,
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
                'message': str(e)
            })

@csrf_exempt
@login_required
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
@login_required
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

@login_required
def checkout(request):
    """Page de commande"""
    cart = get_or_create_cart(request)
    
    if request.method == 'POST':
        # Créer la commande
        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            customer_name=request.POST.get('customer_name'),
            customer_phone=request.POST.get('customer_phone'),
            customer_address=request.POST.get('customer_address'),
            payment_method=request.POST.get('payment_method'),
            total_amount=cart.get_total()
        )
        
        # Créer les articles de commande et mettre à jour le stock
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.get_current_price(),
                selected_size=cart_item.selected_size
            )
            
            # Mettre à jour le stock du produit
            cart_item.product.quantity -= cart_item.quantity
            cart_item.product.save()
        
        # Vider le panier
        cart.items.all().delete()
        
        messages.success(request, 'Commande passée avec succès!')
        return redirect('shop:index')
    
    context = {
        'cart': cart,
    }
    return render(request, 'shop/checkout.html', context)

@login_required
def contact_view(request):
    """Page de contact"""
    if request.method == 'POST':
        Contact.objects.create(
            name=request.POST.get('name'),
            phone=request.POST.get('phone', ''),
            message=request.POST.get('message')
        )
        messages.success(request, 'Message envoyé avec succès!')
        return redirect('shop:contact')
    
    return render(request, 'shop/contact.html', context)

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
        
        # Authentification par email
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
        
        # Validation
        if password != confirm_password:
            return JsonResponse({
                'success': False,
                'message': 'Les mots de passe ne correspondent pas!'
            })
        
        # Vérifier si l'email existe déjà
        if User.objects.filter(email=email).exists():
            return JsonResponse({
                'success': False,
                'message': 'Un compte existe déjà avec cet email!'
            })
        
        try:
            # Créer l'utilisateur
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
            
            # Connecter automatiquement l'utilisateur après l'inscription
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

@csrf_exempt
def reset_password(request):
    """Vue pour réinitialiser le mot de passe"""
    if request.method == 'POST':
        data = json.loads(request.body)
        email = data.get('email')
        
        try:
            user = User.objects.get(email=email)
            # Ici, vous pouvez implémenter la logique d'envoi d'email
            # Pour l'instant, on retourne juste un message de succès
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

# Vues Admin
@staff_member_required
def admin_dashboard(request):
    """Dashboard admin personnalisé"""
    products = Product.objects.all()
    categories = Category.objects.all()
    orders = Order.objects.all()[:10]  # 10 dernières commandes
    contacts = Contact.objects.filter(is_read=False).count()
    
    context = {
        'products': products,
        'categories': categories,
        'orders': orders,
        'total_products': products.count(),
        'total_categories': categories.count(),
        'total_orders': Order.objects.count(),
        'unread_messages': contacts,
    }
    return render(request, 'shop/admin/dashboard.html', context)

@staff_member_required
def admin_products(request):
    """Liste des produits pour l'admin"""
    products = Product.objects.all()
    context = {
        'products': products,
    }
    return render(request, 'shop/admin/products.html', context)

@staff_member_required
def admin_add_product(request):
    """Ajouter un produit"""
    if request.method == 'POST':
        try:
            # Créer le produit
            product = Product.objects.create(
                name=request.POST.get('name'),
                description=request.POST.get('description'),
                price=request.POST.get('price'),
                sale_price=request.POST.get('sale_price') if request.POST.get('on_sale') else None,
                on_sale=bool(request.POST.get('on_sale')),
                category_id=request.POST.get('category'),
                quantity=request.POST.get('quantity', 0),
                sizes=json.loads(request.POST.get('sizes', '[]')),
            )
            
            # Gérer les images
            images = request.FILES.getlist('images')
            for i, image in enumerate(images[:5]):  # Limiter à 5 images
                ProductImage.objects.create(
                    product=product,
                    image=image,
                    order=i,
                    is_primary=(i == 0)
                )
            
            messages.success(request, 'Produit ajouté avec succès!')
            return redirect('shop:admin_products')
            
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    categories = Category.objects.all()
    context = {
        'categories': categories,
    }
    return render(request, 'shop/admin/add_product.html', context)

@staff_member_required
def admin_edit_product(request, product_id):
    """Modifier un produit"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        try:
            product.name = request.POST.get('name')
            product.description = request.POST.get('description')
            product.price = request.POST.get('price')
            product.sale_price = request.POST.get('sale_price') if request.POST.get('on_sale') else None
            product.on_sale = bool(request.POST.get('on_sale'))
            product.category_id = request.POST.get('category')
            product.quantity = request.POST.get('quantity', 0)
            product.sizes = json.loads(request.POST.get('sizes', '[]'))
            product.save()
            
            # Gérer les nouvelles images
            images = request.FILES.getlist('images')
            if images:
                # Obtenir le dernier ordre
                last_order = product.images.order_by('-order').first()
                start_order = (last_order.order + 1) if last_order else 0
                
                for i, image in enumerate(images[:5]):
                    ProductImage.objects.create(
                        product=product,
                        image=image,
                        order=start_order + i
                    )
            
            messages.success(request, 'Produit modifié avec succès!')
            return redirect('shop:admin_products')
            
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    categories = Category.objects.all()
    context = {
        'product': product,
        'categories': categories,
    }
    return render(request, 'shop/admin/edit_product.html', context)

@staff_member_required
def admin_delete_product(request, product_id):
    """Supprimer un produit"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Produit supprimé avec succès!')
        return redirect('shop:admin_products')
    
    return redirect('shop:admin_products')

@staff_member_required
def admin_categories(request):
    """Gérer les catégories"""
    categories = Category.objects.all()
    context = {
        'categories': categories,
    }
    return render(request, 'shop/admin/categories.html', context)

@staff_member_required
def admin_add_category(request):
    """Ajouter une catégorie"""
    if request.method == 'POST':
        try:
            category = Category.objects.create(
                name=request.POST.get('name'),
                icon=request.POST.get('icon', '📦'),
                category_type=request.POST.get('category_type', 'none'),
                attributes=json.loads(request.POST.get('attributes', '[]'))
            )
            messages.success(request, 'Catégorie ajoutée avec succès!')
            return JsonResponse({'success': True, 'id': category.id, 'name': category.name})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})

@staff_member_required
def admin_orders(request):
    """Liste des commandes"""
    orders = Order.objects.all()
    context = {
        'orders': orders,
    }
    return render(request, 'shop/admin/orders.html', context)

@staff_member_required
def admin_order_detail(request, order_id):
    """Détail d'une commande"""
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()
            messages.success(request, 'Statut de la commande mis à jour!')
    
    context = {
        'order': order,
    }
    return render(request, 'shop/admin/order_detail.html', context)