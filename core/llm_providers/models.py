from django.db import models

from shared.base.models import BaseModel


class LLMProviderCodes(models.TextChoices):
    GEMINI = 'gemini', 'Gemini'
    OPENAI = 'openai', 'OpenAI'
    ANTHROPIC = 'anthropic', 'Anthropic'

class LLMProvider(BaseModel):
    """Model for configuring and managing external Large Language Model providers.

    (e.g., OpenAI, Anthropic, Gemini) and their credentials.
    """
    name = models.CharField(max_length=100, unique=True, help_text="e.g. openai, gemini, anthropic")
    code = models.CharField(max_length=50, blank=True, default='', db_index=True, help_text="Unique internal identifier (e.g. OPENAI, GEMINI)")
    enabled = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False, help_text="Fallback provider if none specified")
    api_key = models.CharField(max_length=2048, blank=True, default='')
    model = models.CharField(max_length=100, blank=True, default='', help_text="e.g. gpt-4o, gemini-2.5-flash")
    base_url = models.CharField(max_length=500, blank=True, default='', help_text="e.g. custom proxy URL")
    description = models.TextField(blank=True, default='')
    timeout_seconds = models.IntegerField(default=60)
    max_retries = models.IntegerField(default=3)
    health_check_path = models.CharField(max_length=255, blank=True, help_text="Path to check API health (e.g., '/v1/models')")  # noqa: E501
    health_check_status = models.CharField(max_length=50, blank=True, default='')
    last_health_check = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'llm_providers'
        ordering = ('name',)

    def __init__(self, *args, **kwargs):
        """Initialize the instance and track original field states for changes."""
        super().__init__(*args, **kwargs)
        self._original_base_url = self.base_url
        self._original_health_check_path = self.health_check_path
        self._original_api_key = self.api_key

    def get_decrypted_api_key(self) -> str:
        """Helper to securely decrypt the stored API key."""
        from experience_cloud.api_provider.utils import decrypt_string

        if not self.api_key:
            return ""

        return decrypt_string(self.api_key)

    def save(self, *args, **kwargs):
        """Save the provider, enforce a single default, and encrypt the API key if modified."""
        from experience_cloud.api_provider.utils import encrypt_string

        if self.is_default:
            # Ensure only one default exists
            LLMProvider.objects.filter(is_default=True).update(is_default=False)

        # Encrypt API key if it was changed (meaning it's plain text from the admin form)
        # Also encrypt on creation if it's not already encrypted.
        if self.api_key:
            is_changed = self.api_key != self._original_api_key
            is_new_unencrypted = not self.pk and not self.api_key.startswith(('gAAAAAB', 'b64:'))

            if is_changed or is_new_unencrypted:
                self.api_key = encrypt_string(self.api_key)

        if self.pk and (
            self.base_url != self._original_base_url or
            self.health_check_path != self._original_health_check_path or
            self.api_key != self._original_api_key
        ):
                self.health_check_status = ''

        super().save(*args, **kwargs)

        self._original_base_url = self.base_url
        self._original_health_check_path = self.health_check_path
        self._original_api_key = self.api_key

    def __str__(self):
        """String representation."""
        return f"{self.name} ({self.model})"

class TokenUsageLog(BaseModel):
    """Log of individual interactions with LLM providers.

    Used to track granular token consumption, request types, and estimated cost per request.
    """
    timestamp = models.DateTimeField(auto_now_add=True)
    provider = models.ForeignKey(LLMProvider, on_delete=models.CASCADE, related_name='usage_logs')
    type = models.CharField(max_length=50, blank=True, default='')  # e.g., 'JSON_EXTRACTION', 'TRANSLATION'

    # Cross-Boundary Soft Reference
    brand_id = models.IntegerField(null=True, blank=True)
    brand_name = models.CharField(max_length=255, blank=True, default='')

    # Metrics
    prompt_tokens = models.IntegerField(default=0)
    completion_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0.00)

    class Meta:
        db_table = 'token_usage_logs'
        indexes = (
            models.Index(fields=['timestamp']),
            models.Index(fields=['brand_id', 'timestamp']),
        )

class TokenUsageSummary(BaseModel):
    """Aggregated daily token usage and cost metrics per provider, type, and brand.

    Provides high-level insights without querying large log tables.
    """
    date = models.DateField()
    provider = models.ForeignKey(LLMProvider, on_delete=models.CASCADE, related_name='usage_summaries')
    type = models.CharField(max_length=50, blank=True, default='')

    # Cross-Boundary Soft Reference
    brand_id = models.IntegerField(null=True, blank=True)
    brand_name = models.CharField(max_length=255, blank=True, default='')

    # Aggregated Metrics
    requests = models.IntegerField(default=0)
    prompt_tokens = models.IntegerField(default=0)
    completion_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=6, default=0.00)

    class Meta:
        db_table = 'token_usage_summaries'
        constraints = (
            models.UniqueConstraint(
                fields=['date', 'provider', 'type', 'brand_id'],
                name='unique_token_summary_dimension'
            ),
        )
        indexes = (
            models.Index(fields=['date']),
            models.Index(fields=['brand_id', 'date']),
        )

