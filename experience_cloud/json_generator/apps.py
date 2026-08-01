from django.apps import AppConfig


class JsonGeneratorConfig(AppConfig):
    """Config for JSON generator app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'experience_cloud.json_generator'
    label = 'experience_cloud_json_generator'
