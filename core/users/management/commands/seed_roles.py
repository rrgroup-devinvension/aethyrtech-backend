from django.core.management.base import BaseCommand
from core.users.models import Role

class Command(BaseCommand):
    help = "Seed initial system roles."

    def handle(self, *args, **options):
        # Define the core roles from the UserRole enum
        roles = [
            {'code': 'admin', 'name': 'Administrator', 'role_type': 'INTERNAL', 'permissions': {'all': True}},
            {'code': 'cto', 'name': 'Chief Technology Officer', 'role_type': 'INTERNAL', 'permissions': {'all': True}},
            {'code': 'internal_user', 'name': 'Internal User', 'role_type': 'INTERNAL', 'permissions': {}},
            {'code': 'marketing', 'name': 'Marketing Manager', 'role_type': 'INTERNAL', 'permissions': {}},
            {'code': 'executor', 'name': 'Executor', 'role_type': 'INTERNAL', 'permissions': {}},
        ]

        created_count = 0
        updated_count = 0

        for role_data in roles:
            role, created = Role.objects.get_or_create(
                code=role_data['code'],
                defaults={
                    'name': role_data['name'],
                    'role_type': role_data['role_type'],
                    'permissions': role_data['permissions']
                }
            )
            
            if created:
                created_count += 1
            else:
                # If it already existed, we might want to ensure name and role_type are correct
                if role.name != role_data['name'] or role.role_type != role_data['role_type']:
                    role.name = role_data['name']
                    role.role_type = role_data['role_type']
                    role.save()
                    updated_count += 1

        # Optional: We could remove the old 'Super Admin' role if they want to migrate fully to 'admin'.
        # Role.objects.filter(name='Super Admin').delete()

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded Roles! Created: {created_count}, Updated: {updated_count}"))
