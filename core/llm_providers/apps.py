from django.apps import AppConfig


class LlmProvidersConfig(AppConfig):
    """LLM Providers app config."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.llm_providers'
    label = 'core_llm_providers'
