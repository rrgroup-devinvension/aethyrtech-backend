from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os
class Command(BaseCommand):
    help = "Seed initial data (idempotent)."

    def handle(self, *args, **options):
        User = get_user_model()
        admin_email = os.getenv("ADMIN_EMAIL")
        if not User.objects.filter(email=admin_email).exists():
            User.objects.create_superuser(
                email=admin_email,
                password=os.getenv("ADMIN_PASSWORD"),
                name="Admin User",    # optional
            )
            self.stdout.write(self.style.SUCCESS(f"Created superuser {admin_email}"))
        else:
            self.stdout.write(self.style.WARNING("Superuser already exists; skipping."))
