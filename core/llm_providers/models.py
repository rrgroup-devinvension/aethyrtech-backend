from django.db import models
from shared.base.models import BaseModel

class LLMProvider(BaseModel):
    name = models.CharField(max_length=100, unique=True, help_text="e.g. openai, gemini, anthropic")
    enabled = models.BooleanField(default=False)
    api_key = models.CharField(max_length=255, null=True, blank=True)
    model = models.CharField(max_length=100, null=True, blank=True, help_text="e.g. gpt-4o, gemini-2.5-flash")
    base_url = models.CharField(max_length=500, null=True, blank=True, help_text="e.g. custom proxy URL")
    description = models.TextField(null=True, blank=True)
    timeout_seconds = models.IntegerField(default=60)
    max_retries = models.IntegerField(default=3)
    health_check_path = models.CharField(max_length=255, blank=True, help_text="Path to check API health (e.g., '/v1/models')")
    health_check_status = models.CharField(max_length=50, null=True, blank=True)
    last_health_check = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'llm_providers'
        ordering = ('name',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_base_url = self.base_url
        self._original_health_check_path = self.health_check_path
        self._original_api_key = self.api_key

    def save(self, *args, **kwargs):
        if self.pk:
            if (self.base_url != self._original_base_url or 
                self.health_check_path != self._original_health_check_path or 
                self.api_key != self._original_api_key):
                self.health_check_status = None
        super().save(*args, **kwargs)
        self._original_base_url = self.base_url
        self._original_health_check_path = self.health_check_path
        self._original_api_key = self.api_key

    def __str__(self):
        return f"{self.name} ({self.model})"
