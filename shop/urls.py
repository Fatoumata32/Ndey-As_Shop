from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    # Page d'accueil = Login
    path('', views.login_register_view, name='login'),  
    
    # Authentification
    path('logout/', views.logout_view, name='logout'),
    
    # Pages publiques (accessible après login)
    path('home/', views.index, name='index'),
    path('shop/', views.shop, name='shop'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart_view, name='cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('contact/', views.contact_view, name='contact'),
    
    # API Panier
    path('api/cart/add/', views.add_to_cart, name='add_to_cart'),
    path('api/cart/update/', views.update_cart_item, name='update_cart_item'),
    path('api/cart/remove/', views.remove_from_cart, name='remove_from_cart'),
    
    # API AJAX
    path('api/login/', views.ajax_login, name='ajax_login'),
    path('api/register/', views.ajax_register, name='ajax_register'),
    path('api/reset-password/', views.reset_password, name='reset_password'),
    
    # Admin
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
]