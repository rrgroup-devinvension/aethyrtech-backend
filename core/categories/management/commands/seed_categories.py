from django.core.management.base import BaseCommand

from core.categories.models import Category


class Command(BaseCommand):
    """Django management command to seed the database with default categories.

    Can be run via `python manage.py seed_categories`. Useful for setting up
    initial master data during deployment or development.
    """
    help = "Seed Categories"

    def handle(self, *args, **options):
        """Execute the seeding process.

        Iterates over a predefined list of default categories and uses
        `update_or_create` to ensure idempotency. Outputs the count of
        newly created vs updated records to the standard output.
        """
        categories_data = [
            {"name": "Printers", "description": "Printers"},
            {"name": "Mobile", "description": "Mobile"},
            {"name": "Baby Care", "description": "Baby Care Category"},
            {"name": "Laundry", "description": "Laundry Category"},
            {"name": "Mattress", "description": "Mattress"},
        ]

        created_count = 0
        updated_count = 0

        for data in categories_data:
            _, created = Category.objects.update_or_create(
                name=data["name"],
                defaults={"description": data["description"]}
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded Categories! "
                f"Created: {created_count}, Updated: {updated_count}"
            )
        )
