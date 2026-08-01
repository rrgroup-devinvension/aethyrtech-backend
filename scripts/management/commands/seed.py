import importlib
import os

from django.apps import apps
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Custom management command to dynamically execute all app seeders."""
    help = "Dynamically discover and run 'seed' or 'seed_data' commands from all installed apps."

    def handle(self, *args, **options):
        """Execute the command to find and run seed scripts."""
        self.stdout.write(self.style.NOTICE("Starting global seed process..."))

        apps_seeded = 0

        for app_config in apps.get_app_configs():
            commands_dir = os.path.join(app_config.path, 'management', 'commands')

            if not os.path.isdir(commands_dir):
                continue

            # Find any python file starting with 'seed'
            for filename in os.listdir(commands_dir):
                if filename.startswith('seed') and filename.endswith('.py') and filename != 'seed.py':
                    cmd_name = filename[:-3] # remove .py
                    module_path = f"{app_config.name}.management.commands.{cmd_name}"

                    try:
                        # Attempt to import the command module
                        module = importlib.import_module(module_path)

                        if not hasattr(module, 'Command'):
                            # This happens if a seed file exists but is empty (0 bytes) or scaffolded incorrectly.
                            continue

                        msg = f"\n[{app_config.verbose_name}] Found '{cmd_name}'. Executing..."
                        self.stdout.write(self.style.NOTICE(msg))

                        # Instantiate and run the command explicitly
                        command_instance = module.Command()
                        # Execute skips argument parsing and directly calls handle()
                        command_instance.execute(*args, **options)

                        self.stdout.write(self.style.SUCCESS(f"[{app_config.verbose_name}] Successfully seeded!"))
                        apps_seeded += 1
                    except ImportError:
                        pass
                    except Exception as e:  # noqa: BLE001
                        err_msg = f"[{app_config.verbose_name}] Error executing '{cmd_name}': {e}"
                        self.stdout.write(self.style.ERROR(err_msg))

        if apps_seeded == 0:
            self.stdout.write(self.style.WARNING("\nNo seed scripts found in any apps."))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nGlobal seed process completed. Seeded {apps_seeded} app(s)."))
