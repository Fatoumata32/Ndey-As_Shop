from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify
from datetime import timedelta

class Size(models.Model):
    """Modèle pour les tailles disponibles"""
    SIZE_TYPES = [
        ('standard', 'Taille standard'),
        ('measurement', 'Mesure'),
    ]

    name = models.CharField(max_length=50, unique=True)
    size_type = models.CharField(max_length=20, choices=SIZE_TYPES, default='standard')
    display_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name

class Category(models.Model):
    """Modèle pour les catégories de produits"""
    CATEGORY_TYPES = [
        ('clothing', 'Tailles de vêtements'),
        ('fabric', 'Longueurs de tissu'),
        ('bag', 'Tailles des sacs'),
        ('jewelry', 'Tailles de bijoux'),
        ('shoe', 'Pointures de chaussures'),
        ('none', 'Aucune option de taille'),
    ]

    MEASUREMENT_UNITS = [
        ('meter', 'Mètre'),
        ('cm', 'Centimètre'),
        ('yard', 'Yard'),
        ('piece', 'Pièce'),
    ]
    
    name = models.CharField(max_length=100, unique=True, default='Sans nom')  # Ajout d'une valeur par défaut
    slug = models.SlugField(max_length=150, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPES, default='none')
    measurement_unit = models.CharField(max_length=20, choices=MEASUREMENT_UNITS, default='meter', blank=True, null=True)
    available_sizes = models.ManyToManyField(Size, blank=True, related_name='categories')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_size_label(self):
        """Retourne le label approprié pour les tailles/mesures"""
        if self.category_type == 'fabric':
            return f"Longueur ({self.get_measurement_unit_display()})"
        elif self.category_type == 'clothing':
            return "Taille"
        elif self.category_type == 'shoe':
            return "Pointure"
        elif self.category_type == 'bag':
            return "Taille"
        elif self.category_type == 'jewelry':
            return "Taille"
        else:
            return "Option"

class Product(models.Model):
    """Modèle pour les produits"""
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique=False, blank=True, null=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    on_sale = models.BooleanField(default=False)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    sold_out = models.BooleanField(default=False)
    sizes = models.ManyToManyField(Size, blank=True, related_name='products')
    icon = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Génération automatique du slug - only on creation
        if not self.slug and self.name:
            self.slug = slugify(self.name)
            # Handle slug uniqueness
            base_slug = self.slug
            counter = 1
            while Product.objects.filter(slug=self.slug).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1

        super().save(*args, **kwargs)
    
    def get_current_price(self):
        """Retourne le prix actuel (solde ou normal)"""
        return self.sale_price if self.on_sale and self.sale_price else self.price
    
    @property
    def discount_percent(self):
        """Calcule le pourcentage de remise"""
        if self.on_sale and self.sale_price and self.price > self.sale_price:
            discount = ((self.price - self.sale_price) / self.price) * 100
            return round(discount)
        return 0
    
    @property
    def is_new(self):
        """Détermine si le produit est nouveau (moins de 30 jours)"""
        return self.created_at > timezone.now() - timedelta(days=30)
    
    @property
    def primary_image(self):
        """Retourne l'image principale du produit"""
        return self.images.filter(is_primary=True).first() or self.images.first()
    
    def get_absolute_url(self):
        """Retourne l'URL du produit utilisant le slug"""
        from django.urls import reverse
        return reverse('shop:product_detail', kwargs={'slug': self.slug})

    def get_average_rating(self):
        """Calcule la note moyenne du produit"""
        from django.db.models import Avg
        result = self.reviews.aggregate(average=Avg('rating'))
        return result['average'] or 0

    def get_rating_count(self):
        """Retourne le nombre total d'avis"""
        return self.reviews.count()

    def get_rating_distribution(self):
        """Retourne la distribution des notes"""
        distribution = {}
        for i in range(1, 6):
            distribution[i] = self.reviews.filter(rating=i).count()
        return distribution

class ProductImage(models.Model):
    """Modèle pour les images de produits"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/images/')
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = "Image de produit"
        verbose_name_plural = "Images de produits"

    def __str__(self):
        return f"Image for {self.product.name}"

    def save(self, *args, **kwargs):
        # S'assurer qu'une seule image primaire par produit
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)

class ProductVideo(models.Model):
    """Modèle pour les vidéos de produits"""
    VIDEO_TYPES = [
        ('upload', 'Fichier uploadé'),
        ('youtube', 'Lien YouTube'),
        ('vimeo', 'Lien Vimeo'),
        ('url', 'URL externe'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='videos')
    video_type = models.CharField(max_length=20, choices=VIDEO_TYPES, default='upload')
    video_file = models.FileField(upload_to='products/videos/', blank=True, null=True, help_text="Fichier vidéo (MP4, WebM, etc.)")
    video_url = models.URLField(blank=True, null=True, help_text="URL YouTube, Vimeo ou autre")
    title = models.CharField(max_length=200, blank=True, help_text="Titre de la vidéo")
    description = models.TextField(blank=True, help_text="Description de la vidéo")
    thumbnail = models.ImageField(upload_to='products/video_thumbnails/', blank=True, null=True, help_text="Miniature de la vidéo")
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = "Vidéo de produit"
        verbose_name_plural = "Vidéos de produits"

    def __str__(self):
        return f"Video for {self.product.name} - {self.get_video_type_display()}"

    def get_embed_url(self):
        """Retourne l'URL d'embed pour YouTube/Vimeo"""
        if self.video_type == 'youtube' and self.video_url:
            # Extraire l'ID YouTube
            if 'youtu.be/' in self.video_url:
                video_id = self.video_url.split('youtu.be/')[-1].split('?')[0]
            elif 'youtube.com/watch?v=' in self.video_url:
                video_id = self.video_url.split('watch?v=')[-1].split('&')[0]
            else:
                return self.video_url
            return f"https://www.youtube.com/embed/{video_id}"
        elif self.video_type == 'vimeo' and self.video_url:
            # Extraire l'ID Vimeo
            video_id = self.video_url.split('vimeo.com/')[-1].split('?')[0]
            return f"https://player.vimeo.com/video/{video_id}"
        return self.video_url

class Cart(models.Model):
    """Modèle pour le panier"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Cart #{self.id} - {self.user.username if self.user else 'Anonymous'}"
    
    def get_total(self):
        """Calcule le total du panier"""
        return sum(item.get_subtotal() for item in self.items.all())

class CartItem(models.Model):
    """Modèle pour les articles du panier"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    selected_size = models.CharField(max_length=50, blank=True, null=True, default='')  # Ajout de null=True et default=''
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('cart', 'product', 'selected_size')
    
    def __str__(self):
        size_info = f" - Taille: {self.selected_size}" if self.selected_size else ""
        return f"{self.quantity} x {self.product.name}{size_info}"
    
    def get_subtotal(self):
        """Calcule le sous-total pour cet article"""
        return self.quantity * self.product.get_current_price()

class Order(models.Model):
    """Modèle pour les commandes"""
    PAYMENT_METHODS = [
        ('orange_money', 'Orange Money'),
        ('wave', 'Wave'),
        ('cash', 'Paiement à la livraison'),
    ]

    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('confirmed', 'Confirmée'),
        ('processing', 'En traitement'),
        ('shipped', 'Expédié'),
        ('delivered', 'Livré'),
        ('cancelled', 'Annulé'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    customer_name = models.CharField(max_length=200, null=True, blank=True)
    customer_email = models.EmailField(null=True, blank=True)
    customer_phone = models.CharField(max_length=20, null=True, blank=True)
    customer_address = models.TextField(null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True, null=True)  # Pour les notes de modification
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Propriétés pour la compatibilité avec les templates
    @property
    def name(self):
        return self.customer_name

    @property
    def email(self):
        return self.customer_email

    @property
    def phone(self):
        return self.customer_phone

    @property
    def address(self):
        return self.customer_address

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id} - {self.customer_name}"

class OrderItem(models.Model):
    """Modèle pour les articles d'une commande"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    selected_size = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.quantity} x {self.product.name if self.product else 'Deleted Product'}"

    def get_subtotal(self):
        return self.quantity * self.price

    def get_total(self):
        """Alias pour get_subtotal pour compatibilité avec le template"""
        return self.get_subtotal()

class Contact(models.Model):
    """Modèle pour les messages de contact"""
    name = models.CharField(max_length=200)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Message from {self.name} ({self.email})"

class ProductReview(models.Model):
    """Modèle pour les avis et notations des produits"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('product', 'user')

    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.rating}★)"


class Favorite(models.Model):
    """Modèle pour les produits favoris des utilisateurs"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"