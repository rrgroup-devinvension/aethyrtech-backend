from django.db import models
from shared.base.models import BaseModel

class LLMProvider(BaseModel):
    name = models.CharField(max_length=100, unique=True, help_text="e.g. openai, gemini, anthropic")
    enabled = models.BooleanField(default=False)
    api_key = models.CharField(max_length=255, null=True, blank=True)
    model = models.CharField(max_length=100, null=True, blank=True, help_text="e.g. gpt-4o, gemini-2.5-flash")
    
    class Meta:
        db_table = 'llm_providers'
        ordering = ('name',)

    def __str__(self):
        return f"{self.name} ({self.model})"
