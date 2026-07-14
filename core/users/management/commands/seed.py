from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os
class Command(BaseCommand):
    help = "Seed initial data (idempotent)."

    def handle(self, *args, **options):
        User = get_user_model()
        from core.users.models import Role
        
        # 1. Provide safe defaults if .env is missing
        admin_email = os.getenv("ADMIN_EMAIL", "admin@aethyrtech.com")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        
        # 2. Create the internal Admin role first
        admin_role, _ = Role.objects.get_or_create(
            name="Super Admin",
            defaults={
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
