from typing import Any, TypedDict

from django.core.management.base import BaseCommand

from core.users.models import Role


class RoleData(TypedDict):
    """Type definition for role seed data."""
    code: str
    name: str
    role_type: str
    permissions: dict[str, Any]


class Command(BaseCommand):
    """Django management command to seed the database with initial system roles.

    This script ensures that the foundational roles (like Administrator, CTO,
    and Internal User) exist in the database, updating them if they already
    exist with different names or types.
    """
    help = "Seed initial system roles."

    def handle(self, *args, **options) -> None:
        """Execute the command to populate the database with core role definitions."""
        # Define the core roles from the UserRole enum
        roles: list[RoleData] = [
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

        self.stdout.write(self.style.SUCCESS(
            f"Successfully seeded Roles! Created: {created_count}, Updated: {updated_count}"
        ))
