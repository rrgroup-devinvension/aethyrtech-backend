from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Users App Config."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.users'
    label = 'core_users'
