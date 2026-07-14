from django.core.management.base import BaseCommand
from experience_cloud.catalog.models import Platform

class Command(BaseCommand):
    help = "Seed Platforms"

    def handle(self, *args, **options):
        platforms_data = [
            {"name": "Instamart", "value": "instamart", "platform_type": "quick_commerce", "source": None, "status": "active"},
            {"name": "Zepto", "value": "zepto", "platform_type": "quick_commerce", "source": None, "status": "active"},
            {"name": "Blinkit", "value": "blinkit", "platform_type": "quick_commerce", "source": None, "status": "active"},
            {"name": "Bigbasket", "value": "bigbasket", "platform_type": "quick_commerce", "source": None, "status": "active"},
            {"name": "Amazon Fresh", "value": "amazon_fresh", "platform_type": "quick_commerce", "source": "xbytes", "status": "active"},
            {"name": "Noon Ksa", "value": "noon_ksa", "platform_type": "quick_commerce", "source": "xbytes", "status": "active"},
            {"name": "Amazon", "value": "amazon", "platform_type": "marketplace", "source": "karmatech", "status": "active"},
            {"name": "Amazon Sa", "value": "amazon_sa", "platform_type": "marketplace", "source": "karmatech", "status": "active"},
            {"name": "Flipkart", "value": "flipkart", "platform_type": "marketplace", "source": "karmatech", "status": "active"},
            {"name": "Vijaysales", "value": "vijaysales", "platform_type": "marketplace", "source": "karmatech", "status": "active"},
            {"name": "Reliancedigital", "value": "reliancedigital", "platform_type": "marketplace", "source": "karmatech", "status": "active"},
            {"name": "Croma", "value": "croma", "platform_type": "marketplace", "source": "karmatech", "status": "active"},
            {"name": "Amazon UAE", "value": "amazon_uae", "platform_type": "quick_commerce", "source": "xbytes", "status": "active"},
            {"name": "Noon UAE", "value": "noon_uae", "platform_type": "quick_commerce", "source": "xbytes", "status": "active"},
        ]

        created_count = 0
        updated_count = 0

        for data in platforms_data:
            obj, created = Platform.objects.update_or_create(
                value=data["value"],
                defaults={
                    "name": data["name"],
                    "platform_type": data["platform_type"],
                    "source": data["source"],
                    "status": data["status"]
                }
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded Platforms! Created: {created_count}, Updated: {updated_count}"))
