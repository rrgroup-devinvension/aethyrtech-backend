from django.apps import AppConfig


class CatalogConfig(AppConfig):
    """App config for catalog."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'experience_cloud.catalog'
    label = 'experience_cloud_catalog'
