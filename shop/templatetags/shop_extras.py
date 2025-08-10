# shop/templatetags/shop_extras.py
from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def discount_percent(original_price, sale_price):
    """Calcule le pourcentage de réduction"""
    try:
        original = Decimal(str(original_price))
        sale = Decimal(str(sale_price))
        
        if original > sale and original > 0:
            discount = ((original - sale) / original) * 100
            return round(discount)
        return 0
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def multiply(value, arg):
    """Multiplie deux valeurs"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def subtract(value, arg):
    """Soustrait arg de value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """Divise value par arg"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.simple_tag
def cart_count(request):
    """Retourne le nombre d'articles dans le panier"""
    if request.user.is_authenticated:
        from shop.models import Cart
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            return cart.items.count()
    else:
        # Pour les utilisateurs anonymes, utiliser la session
        session_key = request.session.session_key
        if session_key:
            from shop.models import Cart
            cart = Cart.objects.filter(session_key=session_key).first()
            if cart:
                return cart.items.count()
    return 0

from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def discount_percent(original_price, sale_price):
    """Calcule le pourcentage de réduction"""
    try:
        original = Decimal(str(original_price))
        sale = Decimal(str(sale_price))
        
        if original > sale and original > 0:
            discount = ((original - sale) / original) * 100
            return round(discount)
        return 0
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.simple_tag
def cart_count(request):
    """Retourne le nombre d'articles dans le panier"""
    if request.user.is_authenticated:
        from shop.models import Cart
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            return cart.items.count()
    else:
        session_key = request.session.session_key
        if session_key:
            from shop.models import Cart
            cart = Cart.objects.filter(session_key=session_key).first()
            if cart:
                return cart.items.count()
    return 0