from django.core.management.base import BaseCommand
from experience_cloud.json_generator.models import JsonTemplate
from apps.scheduler.enums import JsonTemplate as JsonTemplateEnum

class Command(BaseCommand):
    help = "Seed JSON Templates from Enum"

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for enum_item in JsonTemplateEnum:
            slug = enum_item.slug
            process_type = enum_item.template_type.value
            
            # Create a pretty name from the slug (e.g., 'brand-audit' -> 'Brand Audit')
            name = slug.replace("-", " ").replace("_", " ").title()

            obj, created = JsonTemplate.objects.update_or_create(
                template=slug,
                defaults={
                    "name": name,
                    "process_type": process_type,
                    "format": "json"  # Default format based on model choices
                }
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded JSON Templates! Created: {created_count}, Updated: {updated_count}"))
