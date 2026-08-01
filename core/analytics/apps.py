from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    """Analytics Config."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.analytics'
    label = 'core_analytics'
