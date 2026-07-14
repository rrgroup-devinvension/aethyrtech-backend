from django.db import models
from shared.base.models import BaseModel

class LLMProvider(BaseModel):
    name = models.CharField(max_length=100, null=True, blank=True)
    model = models.CharField(max_length=100, null=True, blank=True)
    prompt_template = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'llm_providers'
