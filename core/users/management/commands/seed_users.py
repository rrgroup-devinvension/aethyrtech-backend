import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Django management command to seed the database with an initial administrator account."""
    help = "Seed initial data (idempotent)."

    def handle(self, *args, **options):
        """Execute the command to safely create a default system admin user if one does not exist."""
        User = get_user_model()
        from core.users.models import Role

        # 1. Provide safe defaults if .env is missing
        admin_email = os.getenv("ADMIN_EMAIL", "admin@aethyrtech.com")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")

        # 2. Fetch the admin role (should be created by seed_roles.py)
        admin_role, _ = Role.objects.get_or_create(
            code="admin",
            defaults={
                "name": "Administrator",
                "role_type": "INTERNAL",
                "permissions": {"all": True}
            }
        )

        # 3. Create the User safely using the custom model structure
        if not User.objects.filter(email=admin_email).exists():
            user = User(
                email=admin_email,
                name="System Administrator",
                user_type="INTERNAL",
                role=admin_role,
                is_active=True
            )
            # Hash the password properly
            user.set_password(admin_password)
            user.save()

            self.stdout.write(self.style.SUCCESS(f"Successfully created admin user: {admin_email}"))
        else:
            self.stdout.write(self.style.WARNING(f"Admin user {admin_email} already exists; skipping."))
