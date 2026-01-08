# shop/templatetags/shop_extras.py
from django import template
from decimal import Decimal, InvalidOperation
import re
from ..models import Cart

register = template.Library()

@register.filter
def discount_percent(original_price, sale_price):
    """Calcule le pourcentage de réduction"""
    try:
        def to_decimal(val):
            if val is None:
                return None
            s = str(val).strip()
            s = s.replace('\u00A0', '').replace(' ', '')
            s = s.replace(',', '.')
            s = re.sub(r"[^0-9.\-]", "", s)
            if s in ('', '.', '-', '-.'):
                return None
            try:
                return Decimal(s)
            except InvalidOperation:
                return None

        original = to_decimal(original_price)
        sale = to_decimal(sale_price)

        if original is None or sale is None:
            return 0

        if original > sale and original > 0:
            discount = ((original - sale) / original) * 100
            return round(discount)
        return 0
    except (ValueError, TypeError, ZeroDivisionError, InvalidOperation):
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

@register.filter
def currency(value):
    """Formate une valeur en devise"""
    try:
        return f"{int(float(value)):,}".replace(',', ' ')
    except:
        return value

@register.simple_tag
def cart_count(request):
    """Retourne le nombre d'articles dans le panier"""
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            return cart.items.count()
    else:
        session_key = request.session.session_key
        if session_key:
            cart = Cart.objects.filter(session_key=session_key).first()
            if cart:
                return cart.items.count()
    return 0

@register.filter
def cart_item_count(request):
    """Filtre pour obtenir le nombre d'articles dans le panier"""
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            return cart.items.count()
    else:
        session_key = request.session.session_key
        if session_key:
            cart = Cart.objects.filter(session_key=session_key).first()
            if cart:
                return cart.items.count()
    return 0


@register.filter
def star_range(value):
    """Retourne le nombre d'étoiles pleines à afficher"""
    try:
        rating = float(value)
        return int(rating)
    except (ValueError, TypeError):
        return 0


@register.filter
def has_half_star(value):
    """Vérifie s'il faut afficher une demi-étoile"""
    try:
        rating = float(value)
        decimal_part = rating - int(rating)
        return decimal_part >= 0.25 and decimal_part < 0.75
    except (ValueError, TypeError):
        return False


@register.filter
def empty_stars(value):
    """Retourne le nombre d'étoiles vides à afficher"""
    try:
        rating = float(value)
        full_stars = int(rating)
        half_star = 1 if (rating - full_stars) >= 0.25 else 0
        return 5 - full_stars - half_star
    except (ValueError, TypeError):
        return 5


@register.filter
def mul(value, arg):
    """Multiplie deux valeurs"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def div(value, arg):
    """Divise deux valeurs"""
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError):
        return 0
