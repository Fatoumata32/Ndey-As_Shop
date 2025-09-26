from django.core.management.base import BaseCommand
from shop.models import Category, Size, Product


class Command(BaseCommand):
    help = 'Setup default sizes for categories'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up sizes for categories...'))

        # Clothing sizes
        clothing_sizes = [
            'XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL',
            '36', '38', '40', '42', '44', '46', '48', '50'
        ]

        # Shoe sizes
        shoe_sizes = [
            '35', '36', '37', '38', '39', '40', '41', '42', '43', '44', '45', '46'
        ]

        # Fabric lengths (in meters)
        fabric_sizes = [
            '1m', '1.5m', '2m', '2.5m', '3m', '3.5m', '4m', '5m', '6m', '10m'
        ]

        # Bag sizes
        bag_sizes = [
            'Mini', 'Petit', 'Moyen', 'Grand', 'Extra Large'
        ]

        # Jewelry sizes
        jewelry_sizes = [
            'XS (14-15cm)', 'S (16-17cm)', 'M (18-19cm)', 'L (20-21cm)', 'XL (22-23cm)', 'Réglable'
        ]

        # Create sizes if they don't exist
        for size_name in clothing_sizes + shoe_sizes + fabric_sizes + bag_sizes + jewelry_sizes:
            size, created = Size.objects.get_or_create(name=size_name)
            if created:
                self.stdout.write(f'Created size: {size_name}')

        # Get all Size objects
        clothing_size_objects = Size.objects.filter(name__in=clothing_sizes)
        shoe_size_objects = Size.objects.filter(name__in=shoe_sizes)
        fabric_size_objects = Size.objects.filter(name__in=fabric_sizes)
        bag_size_objects = Size.objects.filter(name__in=bag_sizes)
        jewelry_size_objects = Size.objects.filter(name__in=jewelry_sizes)

        # Update categories with appropriate sizes
        for category in Category.objects.all():
            if category.category_type == 'clothing':
                category.available_sizes.set(clothing_size_objects)
                self.stdout.write(f'Added clothing sizes to {category.name}')

            elif category.category_type == 'shoe':
                category.available_sizes.set(shoe_size_objects)
                self.stdout.write(f'Added shoe sizes to {category.name}')

            elif category.category_type == 'fabric':
                category.available_sizes.set(fabric_size_objects)
                self.stdout.write(f'Added fabric sizes to {category.name}')

            elif category.category_type == 'bag':
                category.available_sizes.set(bag_size_objects)
                self.stdout.write(f'Added bag sizes to {category.name}')

            elif category.category_type == 'jewelry':
                category.available_sizes.set(jewelry_size_objects)
                self.stdout.write(f'Added jewelry sizes to {category.name}')

            # For products in this category, add random sizes
            products = Product.objects.filter(category=category)
            for product in products:
                if category.available_sizes.exists() and not product.sizes.exists():
                    # Add some sizes to the product (not all)
                    available = list(category.available_sizes.all())
                    if len(available) > 3:
                        # Select a subset of sizes
                        import random
                        selected_sizes = random.sample(available, min(5, len(available)))
                        product.sizes.set(selected_sizes)
                    else:
                        product.sizes.set(available)
                    self.stdout.write(f'  - Added sizes to product: {product.name}')

        self.stdout.write(self.style.SUCCESS('Successfully set up sizes for categories and products!'))