from django.core.management.base import BaseCommand
from shop.models import Size, Category


class Command(BaseCommand):
    help = 'Configure les tailles et mesures pour les différentes catégories'

    def handle(self, *args, **kwargs):
        # Créer les tailles standards pour vêtements
        clothing_sizes = ['XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL']
        for i, size_name in enumerate(clothing_sizes):
            Size.objects.get_or_create(
                name=size_name,
                defaults={'size_type': 'standard', 'display_order': i}
            )

        # Créer les mesures pour tissus
        fabric_measurements = [
            '0.5 m', '1 m', '1.5 m', '2 m', '2.5 m', '3 m',
            '3.5 m', '4 m', '4.5 m', '5 m', '6 m', '7 m',
            '8 m', '9 m', '10 m'
        ]
        for i, measure in enumerate(fabric_measurements):
            Size.objects.get_or_create(
                name=measure,
                defaults={'size_type': 'measurement', 'display_order': i + 100}
            )

        # Créer les pointures pour chaussures
        shoe_sizes = [
            '35', '36', '37', '38', '39', '40',
            '41', '42', '43', '44', '45', '46'
        ]
        for i, size in enumerate(shoe_sizes):
            Size.objects.get_or_create(
                name=size,
                defaults={'size_type': 'standard', 'display_order': i + 200}
            )

        # Créer les tailles pour sacs
        bag_sizes = ['Petit', 'Moyen', 'Grand', 'Très Grand']
        for i, size in enumerate(bag_sizes):
            Size.objects.get_or_create(
                name=size,
                defaults={'size_type': 'standard', 'display_order': i + 300}
            )

        self.stdout.write(self.style.SUCCESS('Tailles et mesures configurées avec succès!'))

        # Associer les tailles aux catégories existantes
        try:
            # Récupérer ou créer une catégorie tissus exemple
            fabric_category, created = Category.objects.get_or_create(
                name='Tissus',
                defaults={
                    'category_type': 'fabric',
                    'measurement_unit': 'meter',
                    'icon': '🧵'
                }
            )

            if created:
                # Ajouter les mesures de tissu à cette catégorie
                fabric_sizes = Size.objects.filter(size_type='measurement')
                fabric_category.available_sizes.set(fabric_sizes)
                self.stdout.write(self.style.SUCCESS(f'Catégorie Tissus créée avec {fabric_sizes.count()} mesures'))
            else:
                self.stdout.write(self.style.WARNING('La catégorie Tissus existe déjà'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erreur: {e}'))