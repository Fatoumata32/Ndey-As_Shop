# shop/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Sum, Avg
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Category, Product, ProductImage, ProductVideo, Cart, CartItem, Order, OrderItem, Contact, Size, PageView

# Admin Site Configuration
admin.site.site_header = "Ndeyas Shop Administration"
admin.site.site_title = "Ndeyas Shop Admin"
admin.site.index_title = "Tableau de Bord"

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    fields = ['image', 'alt_text', 'order', 'is_primary', 'image_preview']
    readonly_fields = ['image_preview']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="100" style="object-fit: cover; border-radius: 5px;" />', obj.image.url)
        return '-'
    image_preview.short_description = 'Aperçu'

class ProductVideoInline(admin.TabularInline):
    model = ProductVideo
    extra = 1
    fields = ['video_type', 'video_file', 'video_url', 'title', 'thumbnail', 'order']

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        return formset

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category_type', 'created_at']
    list_filter = ['category_type', 'created_at']
    search_fields = ['name']
    ordering = ['name']
    fields = [
        'name',
        'slug',
        'description',
        'category_type',
        'available_sizes'
    ]
    filter_horizontal = ['available_sizes'] 


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['image_tag', 'name', 'category', 'price', 'sale_price', 'on_sale',
                    'stock_status', 'sold_out', 'media_count', 'created_at']
    list_filter = ['category', 'on_sale', 'sold_out', 'created_at']
    search_fields = ['name', 'description', 'slug']
    list_editable = ['price', 'sale_price', 'on_sale']
    inlines = [ProductImageInline, ProductVideoInline]
    ordering = ['-created_at']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at', 'discount_percent', 'is_new', 'media_summary']
    list_per_page = 25
    filter_horizontal = ['sizes']

    fieldsets = (
        ('Informations de base', {
            'fields': ('name', 'slug', 'category', 'description', 'icon')
        }),
        ('Prix et Stock', {
            'fields': ('price', 'sale_price', 'on_sale', 'quantity', 'sold_out')
        }),
        ('Tailles disponibles', {
            'fields': ('sizes',),
            'description': 'Sélectionnez les tailles disponibles pour ce produit selon sa catégorie'
        }),
        ('Médias', {
            'fields': ('media_summary',),
            'description': 'Utilisez les sections ci-dessous pour ajouter des images et vidéos'
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at', 'discount_percent', 'is_new'),
            'classes': ('collapse',)
        }),
    )

    def image_tag(self, obj):
        if obj.primary_image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 5px; border: 2px solid #d81b60;" />',
                obj.primary_image.image.url
            )
        return format_html('<span style="color: #999;">Aucune image</span>')
    image_tag.short_description = 'Image'

    def stock_status(self, obj):
        if obj.sold_out:
            return format_html('<span style="color: white; background: #dc3545; padding: 3px 8px; border-radius: 3px; font-weight: bold;">Épuisé</span>')
        elif obj.quantity <= 5:
            return format_html('<span style="color: #856404; background: #fff3cd; padding: 3px 8px; border-radius: 3px; font-weight: bold;">Stock faible ({})</span>', obj.quantity)
        return format_html('<span style="color: white; background: #28a745; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{} en stock</span>', obj.quantity)
    stock_status.short_description = 'Stock'

    def media_count(self, obj):
        images_count = obj.images.count()
        videos_count = obj.videos.count()
        return format_html(
            '<span style="color: #d81b60; font-weight: bold;">'
            '<i class="fas fa-image"></i> {} | <i class="fas fa-video"></i> {}'
            '</span>',
            images_count, videos_count
        )
    media_count.short_description = 'Médias'

    def media_summary(self, obj):
        if obj.pk:
            images = obj.images.all()
            videos = obj.videos.all()
            html = '<div style="padding: 15px; background: #f8f9fa; border-radius: 8px;">'
            html += f'<h4 style="color: #d81b60; margin-bottom: 10px;">📷 Images ({images.count()})</h4>'
            if images:
                html += '<div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px;">'
                for img in images:
                    primary = '⭐ ' if img.is_primary else ''
                    html += f'<div style="text-align: center;"><img src="{img.image.url}" width="100" style="border-radius: 5px; border: 2px solid {"#d81b60" if img.is_primary else "#ddd"};"><br><small>{primary}#{img.order}</small></div>'
                html += '</div>'
            else:
                html += '<p style="color: #999;">Aucune image ajoutée</p>'

            html += f'<h4 style="color: #d81b60; margin-bottom: 10px;">🎥 Vidéos ({videos.count()})</h4>'
            if videos:
                html += '<ul style="margin: 0; padding-left: 20px;">'
                for video in videos:
                    html += f'<li><strong>{video.get_video_type_display()}</strong>: {video.title or "Sans titre"}</li>'
                html += '</ul>'
            else:
                html += '<p style="color: #999;">Aucune vidéo ajoutée</p>'

            html += '</div>'
            return format_html(html)
        return format_html('<p style="color: #999;">Sauvegardez d\'abord le produit pour ajouter des médias</p>')
    media_summary.short_description = 'Résumé des médias'

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

class PageViewAdmin(admin.ModelAdmin):
    list_display = ['page_url', 'user_display', 'ip_address', 'timestamp']
    list_filter = ['timestamp', 'page_url']
    search_fields = ['page_url', 'ip_address', 'user__username']
    readonly_fields = ['user', 'page_url', 'page_title', 'referrer', 'user_agent', 'ip_address', 'session_id', 'timestamp']
    ordering = ['-timestamp']
    
    def user_display(self, obj):
        if obj.user:
            return format_html('<strong>{}</strong>', obj.user.username)
        return '<em>Anonymous</em>'
    user_display.short_description = 'Utilisateur'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

# PageView is not registered in admin site - use admin_dashboard instead
# admin.site.register(PageView, PageViewAdmin)