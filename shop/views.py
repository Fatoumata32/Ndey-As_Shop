from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from .models import Product, Category, Cart, CartItem, Order, OrderItem, Contact
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
    """Page d'accueil"""
    products = Product.objects.filter(sold_out=False)[:6]  # 6 derniers produits
    categories = Category.objects.all()
    context = {
        'products': products,
        'categories': categories,
    }
    return render(request, 'shop/index.html', context)

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
    
    context = {
        'products': products,
        'categories': categories,
        'current_category': category_filter,
        'search_query': search_query,
    }
    return render(request, 'shop/shop.html', context)

def product_detail(request, product_id):
    """Détail d'un produit"""
    product = get_object_or_404(Product, id=product_id)
    context = {
        'product': product,
    }
    return render(request, 'shop/item.html', context)

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
    
    return render(request, 'shop/contact.html')

def login_view(request):
    """Page de connexion"""
    if request.user.is_authenticated:
        return redirect('shop:index')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # Essayer de se connecter avec l'email comme username
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Connexion réussie!')
            return redirect('shop:index')
        else:
            messages.error(request, 'Email ou mot de passe incorrect.')
    
    return render(request, 'shop/login.html')

def register_view(request):
    """Page d'inscription"""
    if request.user.is_authenticated:
        return redirect('shop:index')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        if password != confirm_password:
            messages.error(request, 'Les mots de passe ne correspondent pas.')
            return render(request, 'shop/login.html')
        
        # Créer l'utilisateur avec l'email comme username
        from django.contrib.auth.models import User
        if User.objects.filter(username=email).exists():
            messages.error(request, 'Cet email est déjà utilisé.')
            return render(request, 'shop/login.html')
        
        user = User.objects.create_user(username=email, email=email, password=password)
        login(request, user)
        messages.success(request, 'Inscription réussie!')
        return redirect('shop:index')
    
    return render(request, 'shop/login.html')

def logout_view(request):
    """Déconnexion"""
    logout(request)
    messages.success(request, 'Déconnexion réussie!')
    return redirect('shop:index')

@login_required
def admin_dashboard(request):
    """Dashboard admin personnalisé"""
    if not request.user.is_staff:
        messages.error(request, 'Accès non autorisé.')
        return redirect('shop:index')
    
    products = Product.objects.all()
    categories = Category.objects.all()
    orders = Order.objects.all()[:10]  # 10 dernières commandes
    
    context = {
        'products': products,
        'categories': categories,
        'orders': orders,
    }
    return render(request, 'shop/admin.html', context)

# views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json

def login_register_view(request):
    """Vue pour afficher la page de connexion/inscription"""
    if request.user.is_authenticated:
        return redirect('shop:home')  # Rediriger vers la page d'accueil si déjà connecté
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
                    'redirect_url': '/shop/'  # URL de redirection après connexion
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
                'redirect_url': '/shop/'
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