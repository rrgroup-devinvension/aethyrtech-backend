from django.apps import AppConfig
import sys


STARTUP_SKIP_COMMANDS = {
    'makemigrations', 'migrate', 'collectstatic', 'test', 'shell',
    'createsuperuser', 'loaddata', 'flush', 'dumpdata'
}


class BrandConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.brand'
    verbose_name = "Brand Management"

    def ready(self):
        """Provision BrandJsonFile rows on app startup when appropriate.

        Guards:
        - Skip when running manage.py commands that operate on migrations/fixtures/tests/shell
        - Skip if DB is not ready (OperationalError / ProgrammingError)
        """
        # Avoid running during migration/management tasks
        if any(cmd in sys.argv for cmd in STARTUP_SKIP_COMMANDS):
            return

        try:
            # Local imports to avoid import-time side effects
            from django.db import OperationalError, ProgrammingError
            from apps.brand.models import Brand
            from apps.scheduler.enums import JsonTemplate
            from apps.scheduler.utility.service_utility import ensure_brand_json_files

            templates = [t.slug for t in JsonTemplate]
            for brand in Brand.objects.all():
                try:
                    ensure_brand_json_files(brand, templates)
                except Exception:
                    # don't break startup; log and continue
                    import logging
                    logging.getLogger(__name__).exception(
                        f"Failed to ensure BrandJsonFile entries for brand {brand.id}"
                    )
        except (OperationalError, ProgrammingError):
            # Database not ready yet; skip provisioning
            return
        except Exception:
            # Catch-all: log but don't prevent app startup
            import logging
            logging.getLogger(__name__).exception("Failed to run Brand startup provisioning")
