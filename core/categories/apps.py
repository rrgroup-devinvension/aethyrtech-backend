from django.apps import AppConfig


class CategoriesConfig(AppConfig):
    """Categories App Config."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.categories'
    label = 'core_categories'
