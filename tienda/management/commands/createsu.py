from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Create a superuser if it does not already exist.'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='admin', help='Username for the superuser')
        parser.add_argument('--email', default='admin@example.com', help='Email for the superuser')
        parser.add_argument('--password', default='Admin123!', help='Password for the superuser')

    def handle(self, *args, **options):
        User = get_user_model()
        username = options['username']
        email = options['email']
        password = options['password']

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f"Superuser '{username}' already exists."))
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Created superuser '{username}' with provided credentials."))
