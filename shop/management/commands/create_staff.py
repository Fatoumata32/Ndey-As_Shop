# shop/management/commands/create_staff.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Crée un utilisateur staff pour accéder à la gestion'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default='admin')
        parser.add_argument('--email', type=str, default='admin@ndeya.com')
        parser.add_argument('--password', type=str, default='admin123')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'L\'utilisateur {username} existe déjà'))
            user = User.objects.get(username=username)
            if not user.is_staff:
                user.is_staff = True
                user.save()
                self.stdout.write(self.style.SUCCESS(f'L\'utilisateur {username} a maintenant les permissions staff'))
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_staff=True
            )
            self.stdout.write(self.style.SUCCESS(f'Utilisateur staff créé avec succès!'))
            self.stdout.write(f'Username: {username}')
            self.stdout.write(f'Password: {password}')
            self.stdout.write(self.style.WARNING('IMPORTANT: Changez le mot de passe après la première connexion'))

        self.stdout.write(self.style.SUCCESS(f'\nVous pouvez maintenant vous connecter à /gestion/tableau-de-bord/ avec ces identifiants'))