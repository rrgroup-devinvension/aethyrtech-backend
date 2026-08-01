from django.apps import AppConfig


class OrganizationsConfig(AppConfig):
    """Organizations App Config."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.organizations'
    label = 'core_organizations'

    def ready(self):
        """Ready app."""
        pass
