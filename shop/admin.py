# shop/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Sum, Avg
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Category, Product, ProductImage, Cart, CartItem, Order, OrderItem, Contact, Size

# Admin Site Configuration
admin.site.site_header = "Ndeyas Shop Administration"
admin.site.site_title = "Ndeyas Shop Admin"
admin.site.index_title = "Tableau de Bord"

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


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['image_tag', 'name', 'category', 'price', 'sale_price', 'on_sale',
                    'stock_status', 'sold_out', 'created_at']
    list_filter = ['category', 'on_sale', 'sold_out', 'created_at']
    search_fields = ['name', 'description', 'slug']
    list_editable = ['price', 'sale_price', 'on_sale']
    inlines = [ProductImageInline]
    ordering = ['-created_at']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at', 'discount_percent', 'is_new']
    list_per_page = 25

    fieldsets = (
        ('Informations de base', {
            'fields': ('name', 'slug', 'category', 'description', 'icon')
        }),
        ('Prix et Stock', {
            'fields': ('price', 'sale_price', 'on_sale', 'quantity', 'sold_out')
        }),
        ('Tailles', {
            'fields': ('sizes',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at', 'discount_percent', 'is_new'),
            'classes': ('collapse',)
        }),
    )

    def image_tag(self, obj):
        if obj.primary_image:
            return format_html('<img src="{}" width="50" height="50" />', obj.primary_image.image.url)
        return '-'
    image_tag.short_description = 'Image'

    def stock_status(self, obj):
        if obj.sold_out:
            return format_html('<span style="color: red;">Épuisé</span>')
        elif obj.quantity <= 5:
            return format_html('<span style="color: orange;">Stock faible ({})< /span>', obj.quantity)
        return format_html('<span style="color: green;">{}</span>', obj.quantity)
    stock_status.short_description = 'Stock'

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
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['customer_name', 'customer_phone', 'customer_email', 'customer_address']
    list_editable = ['status']
    inlines = [OrderItemInline]
    readonly_fields = ['created_at', 'updated_at', 'total_amount']
    ordering = ['-created_at']
    list_per_page = 30
    date_hierarchy = 'created_at'
    list_display = ('id', 'user', 'status', 'created_at')
    list_editable = ('status',)

    fieldsets = (
        ('Informations Client', {
            'fields': ('user', 'customer_name', 'customer_email', 'customer_phone', 'customer_address')
        }),
        ('Détails Commande', {
            'fields': ('status', 'payment_method', 'total_amount')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def status_colored(self, obj):
        colors = {
            'pending': 'orange',
            'processing': 'blue',
            'shipped': 'purple',
            'delivered': 'green',
            'cancelled': 'red'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_colored.short_description = 'Statut'

    actions = ['mark_as_processing', 'mark_as_shipped', 'mark_as_delivered', 'mark_as_cancelled']

    def mark_as_processing(self, request, queryset):
        queryset.update(status='processing')
        self.message_user(request, f"{queryset.count()} commande(s) marquée(s) en traitement.")
    mark_as_processing.short_description = "Marquer comme en traitement"

    def mark_as_shipped(self, request, queryset):
        queryset.update(status='shipped')
        self.message_user(request, f"{queryset.count()} commande(s) marquée(s) comme expédiée(s).")
    mark_as_shipped.short_description = "Marquer comme expédié"

    def mark_as_delivered(self, request, queryset):
        queryset.update(status='delivered')
        self.message_user(request, f"{queryset.count()} commande(s) marquée(s) comme livrée(s).")
    mark_as_delivered.short_description = "Marquer comme livré"

    def mark_as_cancelled(self, request, queryset):
        queryset.update(status='cancelled')
        self.message_user(request, f"{queryset.count()} commande(s) annulée(s).")
    mark_as_cancelled.short_description = "Annuler la commande"

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['name', 'phone', 'email', 'message']
    list_editable = ['is_read']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
    list_per_page = 50

    actions = ['mark_as_read', 'mark_as_unread']

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
        self.message_user(request, f"{queryset.count()} message(s) marqué(s) comme lu(s).")
    mark_as_read.short_description = "Marquer comme lu"

    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
        self.message_user(request, f"{queryset.count()} message(s) marqué(s) comme non lu(s).")
    mark_as_unread.short_description = "Marquer comme non lu"

@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    ordering = ['name']
