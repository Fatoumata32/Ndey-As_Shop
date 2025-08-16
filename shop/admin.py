# shop/admin.py
from django.contrib import admin
from .models import Category, Product, ProductImage, Cart, CartItem, Order, OrderItem, Contact

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'order', 'is_primary']  # Ajout du champ is_primary

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'category_type', 'created_at']
    list_filter = ['category_type', 'created_at']
    search_fields = ['name']
    ordering = ['name']
    fields = [
        'name', 
        'slug', 
        'description', 
        'icon', 
        'category_type', 
        'available_sizes'
    ]
    filter_horizontal = ['available_sizes'] 

# SUPPRIMER cette ligne en double ↓
# admin.site.register(Category, CategoryAdmin)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'sale_price', 'on_sale', 
                    'quantity', 'sold_out', 'created_at']
    list_filter = ['category', 'on_sale', 'sold_out', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['price', 'sale_price', 'on_sale', 'quantity']
    inlines = [ProductImageInline]
    ordering = ['-created_at']

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'order', 'is_primary', 'created_at']  # Ajout de is_primary
    list_filter = ['created_at', 'is_primary']
    search_fields = ['product__name']
    list_editable = ['order', 'is_primary']  # Permet d'éditer directement

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'selected_size']

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'session_key', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__username', 'user__email', 'session_key']
    inlines = [CartItemInline]
    readonly_fields = ['created_at', 'updated_at']

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'price', 'selected_size']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer_name', 'customer_phone', 'status', 
                    'payment_method', 'total_amount', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['customer_name', 'customer_phone', 'customer_address']
    list_editable = ['status']
    inlines = [OrderItemInline]
    readonly_fields = ['created_at', 'updated_at', 'total_amount']
    ordering = ['-created_at']

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'is_read', 'created_at']  # Ajout de email
    list_filter = ['is_read', 'created_at']
    search_fields = ['name', 'phone', 'email', 'message']  # Ajout de email
    list_editable = ['is_read']
    ordering = ['-created_at']
    readonly_fields = ['created_at']  # Correction: suppression de la virgule en trop