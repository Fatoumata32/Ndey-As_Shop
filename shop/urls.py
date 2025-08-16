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
    
    # Panier (AJAX)
    path('ajax/add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('ajax/update-cart/', views.update_cart_item, name='update_cart_item'),
    path('ajax/remove-from-cart/', views.remove_from_cart, name='remove_from_cart'),
    
    # Administration
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # Produits
    path('admin/products/', views.product_list, name='product_list'),
    path('admin/products/add/', views.product_add, name='product_add'),
    path('admin/products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('admin/products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('admin/products/<int:pk>/toggle-status/', views.product_toggle_status, name='product_toggle_status'),
    path('admin/product-images/<int:pk>/delete/', views.product_image_delete, name='product_image_delete'),
    
    # Catégories
    path('admin/categories/', views.category_list, name='category_list'),
    path('admin/categories/add/', views.category_add, name='category_add'),
    path('admin/categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('admin/categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    
    # Commandes
    path('admin/orders/', views.order_list, name='order_list'),
    path('admin/orders/<int:pk>/', views.order_detail, name='order_detail'),
]