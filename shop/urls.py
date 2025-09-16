# shop/urls.py
from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    # Vues publiques
    path('', views.login_register_view, name='login'),
    path('home/', views.index, name='index'),
    path('shop/', views.shop, name='shop'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart_view, name='cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('contact/', views.contact_view, name='contact'),
    
    # Authentification
    path('ajax/login/', views.ajax_login, name='ajax_login'),
    path('ajax/register/', views.ajax_register, name='ajax_register'),
    path('logout/', views.logout_view, name='logout'),
    path('reset-password/', views.reset_password, name='reset_password'),

    # Compte utilisateur
    path('mon-profil/', views.user_profile, name='user_profile'),
    path('mes-commandes/', views.user_orders, name='user_orders'),
    
    # Panier (AJAX)
    path('ajax/add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('ajax/update-cart/', views.update_cart_item, name='update_cart_item'),
    path('ajax/remove-from-cart/', views.remove_from_cart, name='remove_from_cart'),
    
    # Administration (Gestion de la boutique)
    path('gestion/tableau-de-bord/', views.admin_dashboard, name='admin_dashboard'),
    
    # Produits
    path('gestion/produits/', views.product_list, name='product_list'),
    path('gestion/produits/ajouter/', views.product_add, name='product_add'),
    path('gestion/produits/<int:pk>/modifier/', views.product_edit, name='product_edit'),
    path('gestion/produits/<int:pk>/supprimer/', views.product_delete, name='product_delete'),
    path('gestion/produits/<int:pk>/toggle-status/', views.product_toggle_status, name='product_toggle_status'),
    path('gestion/product-images/<int:pk>/delete/', views.product_image_delete, name='product_image_delete'),

    # Catégories
    path('gestion/categories/', views.category_list, name='category_list'),
    path('gestion/categories/ajouter/', views.category_add, name='category_add'),
    path('gestion/categories/<int:pk>/modifier/', views.category_edit, name='category_edit'),
    path('gestion/categories/<int:pk>/supprimer/', views.category_delete, name='category_delete'),

    # Commandes
    path('gestion/commandes/', views.order_list, name='order_list'),
    path('gestion/commandes/<int:pk>/', views.order_detail, name='order_detail'),

    # Messages de contact
    path('gestion/messages/', views.contact_list, name='contact_list'),
    path('gestion/messages/<int:pk>/', views.contact_detail, name='contact_detail'),
    path('gestion/messages/<int:pk>/toggle-read/', views.contact_toggle_read, name='contact_toggle_read'),
    path('gestion/messages/<int:pk>/supprimer/', views.contact_delete, name='contact_delete'),
    path('gestion/messages/marquer-tout-lu/', views.contact_mark_all_read, name='contact_mark_all_read'),
]