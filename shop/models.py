from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

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
    
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, default='📦')
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPES, default='none')
    attributes = models.JSONField(default=list, blank=True)  # Pour stocker les tailles disponibles
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.icon} {self.name}"


class Product(models.Model):
    """Modèle pour les produits"""
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    on_sale = models.BooleanField(default=False)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    quantity = models.IntegerField(default=0)
    sold_out = models.BooleanField(default=False)
    sizes = models.JSONField(default=list, blank=True)  # Tailles disponibles pour ce produit
    icon = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Marquer automatiquement comme épuisé si quantité = 0
        if self.quantity == 0:
            self.sold_out = True
        else:
            self.sold_out = False
            
        # S'assurer que sizes est toujours une liste
        if self.sizes is None:
            self.sizes = []
        elif isinstance(self.sizes, str):
            try:
                import json
                self.sizes = json.loads(self.sizes)
            except:
                self.sizes = []
        elif not isinstance(self.sizes, list):
            self.sizes = []
            
        super().save(*args, **kwargs)
    
    def get_current_price(self):
        """Retourne le prix actuel (solde ou normal)"""
        if self.on_sale and self.sale_price:
            return self.sale_price
        return self.price
    
    def get_sizes_list(self):
        """Retourne les tailles comme une liste Python"""
        if not self.sizes:
            return []
        
        # Si c'est déjà une liste, la retourner
        if isinstance(self.sizes, list):
            return self.sizes
        
        # Si c'est une chaîne JSON, la parser
        if isinstance(self.sizes, str):
            try:
                import json
                sizes = json.loads(self.sizes)
                return sizes if isinstance(sizes, list) else []
            except:
                return []
        
        # Pour tout autre type, retourner une liste vide
        return []
    
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
        from django.utils import timezone
        from datetime import timedelta
        return self.created_at > timezone.now() - timedelta(days=30)
    
    @property
    def primary_image(self):
        """Retourne l'image principale du produit"""
        return self.images.filter(is_primary=True).first() or self.images.first()
    
    def has_size(self, size):
        """Vérifie si une taille spécifique est disponible"""
        return size in self.get_sizes_list()
    
    def is_in_stock(self):
        """Vérifie si le produit est en stock"""
        return self.quantity > 0 and not self.sold_out
    
    def can_purchase(self, quantity=1):
        """Vérifie si on peut acheter une certaine quantité"""
        return self.is_in_stock() and self.quantity >= quantity
    
    def reduce_stock(self, quantity):
        """Réduit le stock après un achat"""
        if self.can_purchase(quantity):
            self.quantity -= quantity
            self.save()
            return True
        return False
    
    def get_absolute_url(self):
        """Retourne l'URL du produit"""
        from django.urls import reverse
        return reverse('shop:product_detail', kwargs={'product_id': self.id})

class ProductImage(models.Model):
    """Modèle pour les images de produits"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return f"Image for {self.product.name}"


class Cart(models.Model):
    """Modèle pour le panier"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        if self.user:
            return f"Cart for {self.user.username}"
        return f"Cart {self.session_key}"
    
    def get_total(self):
        """Calcule le total du panier"""
        total = 0
        for item in self.items.all():
            total += item.get_subtotal()
        return total


class CartItem(models.Model):
    """Modèle pour les articles du panier"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    selected_size = models.CharField(max_length=50, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('cart', 'product', 'selected_size')
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
    
    def get_subtotal(self):
        """Calcule le sous-total pour cet article"""
        return self.quantity * self.product.get_current_price()


class Order(models.Model):
    """Modèle pour les commandes"""
    PAYMENT_METHODS = [
        ('orange-money', 'Orange Money'),
        ('wave', 'Wave'),
        ('cash', 'Paiement à la livraison'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('processing', 'En traitement'),
        ('shipped', 'Expédié'),
        ('delivered', 'Livré'),
        ('cancelled', 'Annulé'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    customer_name = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=20)
    customer_address = models.TextField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order #{self.id} - {self.customer_name}"


class OrderItem(models.Model):
    """Modèle pour les articles d'une commande"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    selected_size = models.CharField(max_length=50, blank=True)
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
    
    def get_subtotal(self):
        return self.quantity * self.price


class Contact(models.Model):
    """Modèle pour les messages de contact"""
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Message from {self.name} - {self.created_at.strftime('%Y-%m-%d')}"
    


# Dans models.py, ajoutez ces propriétés à votre modèle Product :

@property
def discount_percent(self):
    """Calcule le pourcentage de remise"""
    if self.on_sale and self.sale_price and self.price > self.sale_price:
        return round(((self.price - self.sale_price) / self.price) * 100)
    return 0

@property 
def is_new(self):
    """Détermine si le produit est nouveau (moins de 30 jours)"""
    from django.utils import timezone
    from datetime import timedelta
    return self.created_at > timezone.now() - timedelta(days=30)