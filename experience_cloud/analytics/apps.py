from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    """Analytics app config."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'experience_cloud.analytics'
    label = 'experience_cloud_analytics'
