from django.core.management.base import BaseCommand
from experience_cloud.catalog.models import Platform

class Command(BaseCommand):
    help = "Seed Platforms"

    def handle(self, *args, **options):
        platforms_data = [
            {"name": "Instamart", "code": "instamart", "platform_type": "quick_commerce", "source": None, "status": "active"},
            {"name": "Zepto", "code": "zepto", "platform_type": "quick_commerce", "source": None, "status": "active"},
            {"name": "Blinkit", "code": "blinkit", "platform_type": "quick_commerce", "source": None, "status": "active"},
            {"name": "Bigbasket", "code": "bigbasket", "platform_type": "quick_commerce", "source": None, "status": "active"},
            {"name": "Amazon Fresh", "code": "amazon_fresh", "platform_type": "quick_commerce", "source": "xbytes", "status": "active"},
            {"name": "Noon Ksa", "code": "noon_ksa", "platform_type": "quick_commerce", "source": "xbytes", "status": "active"},
            {"name": "Amazon", "code": "amazon", "platform_type": "marketplace", "source": "karmatech", "status": "active"},
            {"name": "Amazon Sa", "code": "amazon_sa", "platform_type": "marketplace", "source": "karmatech", "status": "active"},
            {"name": "Flipkart", "code": "flipkart", "platform_type": "marketplace", "source": "karmatech", "status": "active"},
            {"name": "Vijaysales", "code": "vijaysales", "platform_type": "marketplace", "source": "karmatech", "status": "active"},
            {"name": "Reliancedigital", "code": "reliancedigital", "platform_type": "marketplace", "source": "karmatech", "status": "active"},
            {"name": "Croma", "code": "croma", "platform_type": "marketplace", "source": "karmatech", "status": "active"},
            {"name": "Amazon UAE", "code": "amazon_uae", "platform_type": "quick_commerce", "source": "xbytes", "status": "active"},
            {"name": "Noon UAE", "code": "noon_uae", "platform_type": "quick_commerce", "source": "xbytes", "status": "active"},
        ]

        created_count = 0
        updated_count = 0

        for data in platforms_data:
            obj, created = Platform.objects.update_or_create(
                code=data["code"],
                defaults={
                    "name": data["name"],
                    "platform_type": data["platform_type"],
                    "status": data["status"]
                }
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded Platforms! Created: {created_count}, Updated: {updated_count}"))
