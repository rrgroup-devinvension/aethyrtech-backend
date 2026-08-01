from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    """Authentication Config."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.authentication'
    label = 'core_authentication'
