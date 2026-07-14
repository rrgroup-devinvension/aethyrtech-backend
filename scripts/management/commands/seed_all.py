import importlib
import logging
from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Discovers and runs seed_data() in all installed apps, or a specific app."

    def add_arguments(self, parser):
        parser.add_argument(
            '--app',
            type=str,
            help='Run seed data for a specific app only (e.g., core.users)',
        )

    def handle(self, *args, **options):
        target_app = options.get('app')

        if target_app:
            self.stdout.write(self.style.NOTICE(f"Running seeder for {target_app}..."))
            self._run_seeder(target_app)
        else:
            self.stdout.write(self.style.NOTICE("Running all seeders..."))
            for app_name in settings.INSTALLED_APPS:
                # We only want to run seeders for local apps, not third-party packages.
                # Adjust the filter if your local apps don't start with these prefixes.
                if app_name.startswith('core') or app_name.startswith('experience_cloud') or \
                   app_name.startswith('identity_cloud') or app_name.startswith('media_cloud') or \
                   app_name.startswith('shared'):
                    self._run_seeder(app_name)

        self.stdout.write(self.style.SUCCESS("Seeding process completed!"))

    def _run_seeder(self, app_name):
        try:
            # Dynamically import the seed module
            seed_module = importlib.import_module(f"{app_name}.seed")
            
            if hasattr(seed_module, 'seed_data'):
                self.stdout.write(f"  Executing {app_name}.seed.seed_data()...")
                seed_module.seed_data()
                self.stdout.write(self.style.SUCCESS(f"  Successfully seeded {app_name}"))
            else:
                self.stdout.write(self.style.WARNING(f"  {app_name}.seed exists, but has no seed_data() function."))
        
        except ModuleNotFoundError:
            # Expected behavior if the app doesn't have a seed.py file
            pass
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Error seeding {app_name}: {str(e)}"))
            logger.error("Seeding failed for %s", app_name, exc_info=True)
