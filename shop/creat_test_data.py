# create_test_data.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ndeyas_shop.settings')
django.setup()

from shop.models import Category, Product, Size
from decimal import Decimal

def create_test_data():
    print("Création des données de test...")
    
    # Créer des tailles
    sizes_list = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
    sizes = []
    for size_name in sizes_list:
        size, created = Size.objects.get_or_create(name=size_name)
        sizes.append(size)
        if created:
            print(f"Taille créée: {size_name}")
    
    # Créer des catégories
    categories_data = [
        {
            'name': 'Vêtements',
            'description': 'Vêtements traditionnels et modernes',
            'icon': '👕'
        },
        {
            'name': 'Tissus',
            'description': 'Tissus wax et autres tissus africains',
            'icon': '🧵'
        },
        {
            'name': 'Sacs',
            'description': 'Sacs à main et accessoires',
            'icon': '👜'
        },
        {
            'name': 'Bijoux',
            'description': 'Bijoux traditionnels africains',
            'icon': '💍'
        },
        {
            'name': 'Chaussures',
            'description': 'Chaussures et sandales',
            'icon': '👠'
        }
    ]
    
    for cat_data in categories_data:
        category, created = Category.objects.get_or_create(
            name=cat_data['name'],
            defaults={
                'description': cat_data['description'],
                'icon': cat_data['icon']
            }
        )
        if created:
            print(f"Catégorie créée: {cat_data['name']}")
    
    # Créer des produits
    products_data = [
        {
            'name': 'Robe Wax Élégante',
            'description': 'Magnifique robe en tissu wax avec motifs traditionnels africains. Parfaite pour les occasions spéciales.',
            'price': Decimal('25000'),
            'category': 'Vêtements',
            'quantity': 15,
            'on_sale': True,
            'sale_price': Decimal('20000')
        },
        {
            'name': 'Boubou Homme Brodé',
            'description': 'Boubou traditionnel pour homme avec broderies dorées. Tissu de haute qualité.',
            'price': Decimal('35000'),
            'category': 'Vêtements',
            'quantity': 10
        },
        {
            'name': 'Tissu Wax Holland',
            'description': 'Tissu wax authentique Holland, 6 yards. Motifs colorés et résistants.',
            'price': Decimal('15000'),
            'category': 'Tissus',
            'quantity': 25
        },
        {
            'name': 'Sac à Main en Cuir',
            'description': 'Sac à main en cuir véritable avec motifs africains. Fait main par des artisans locaux.',
            'price': Decimal('18000'),
            'category': 'Sacs',
            'quantity': 8,
            'on_sale': True,
            'sale_price': Decimal('15000')
        },
        {
            'name': 'Collier Perles Traditionnelles',
            'description': 'Collier en perles traditionnelles multicolores. Pièce unique faite à la main.',
            'price': Decimal('8000'),
            'category': 'Bijoux',
            'quantity': 20
        },
        {
            'name': 'Sandales en Cuir',
            'description': 'Sandales confortables en cuir naturel. Design moderne avec touches traditionnelles.',
            'price': Decimal('12000'),
            'category': 'Chaussures',
            'quantity': 12
        },
        {
            'name': 'Ensemble Pagne Femme',
            'description': 'Ensemble complet pagne pour femme : jupe et haut assortis. Coupe moderne.',
            'price': Decimal('22000'),
            'category': 'Vêtements',
            'quantity': 5
        },
        {
            'name': 'Bracelet en Bronze',
            'description': 'Bracelet artisanal en bronze avec gravures traditionnelles.',
            'price': Decimal('5000'),
            'category': 'Bijoux',
            'quantity': 30
        }
    ]
    
    for prod_data in products_data:
        category = Category.objects.get(name=prod_data['category'])
        
        # Extraire les données du produit
        product_fields = {
            'name': prod_data['name'],
            'description': prod_data['description'],
            'price': prod_data['price'],
            'category': category,
            'quantity': prod_data['quantity'],
            'on_sale': prod_data.get('on_sale', False),
        }
        
        if prod_data.get('sale_price'):
            product_fields['sale_price'] = prod_data['sale_price']
        
        product, created = Product.objects.get_or_create(
            name=prod_data['name'],
            defaults=product_fields
        )
        
        if created:
            # Ajouter des tailles pour les vêtements
            if category.name == 'Vêtements':
                product.sizes.set(sizes[1:5])  # S, M, L, XL
            
            print(f"Produit créé: {prod_data['name']}")
        else:
            # Mettre à jour le produit existant
            for key, value in product_fields.items():
                setattr(product, key, value)
            product.save()
            print(f"Produit mis à jour: {prod_data['name']}")
    
    print("\nDonnées de test créées avec succès!")
    print(f"Total catégories: {Category.objects.count()}")
    print(f"Total produits: {Product.objects.count()}")
    print(f"Total tailles: {Size.objects.count()}")

if __name__ == '__main__':
    create_test_data()