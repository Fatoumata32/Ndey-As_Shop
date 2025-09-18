from .models import Cart
from django.db.models import Sum

def cart_count(request):
    """Context processor pour afficher le nombre total d'articles dans le panier"""
    count = 0

    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            # Get total quantity of all items in cart
            count = cart.items.aggregate(total=Sum('quantity'))['total'] or 0
        except Cart.DoesNotExist:
            pass
    else:
        session_key = request.session.session_key
        if session_key:
            try:
                cart = Cart.objects.get(session_key=session_key)
                # Get total quantity of all items in cart
                count = cart.items.aggregate(total=Sum('quantity'))['total'] or 0
            except Cart.DoesNotExist:
                pass

    return {
        'cart_count': count
    }