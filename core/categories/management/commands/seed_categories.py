from django.core.management.base import BaseCommand
from core.categories.models import Category

class Command(BaseCommand):
    help = "Seed Categories"

    def handle(self, *args, **options):
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
            obj, created = Category.objects.update_or_create(
                name=data["name"],
                defaults={"description": data["description"]}
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded Categories! Created: {created_count}, Updated: {updated_count}"))
