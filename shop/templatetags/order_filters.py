from django import template

register = template.Library()

@register.filter
def filter_by_status(orders, status):
    """Filtre les commandes par statut"""
    return [order for order in orders if order.status == status]

@register.filter
def count_by_status(orders, status):
    """Compte les commandes par statut"""
    return len([order for order in orders if order.status == status])