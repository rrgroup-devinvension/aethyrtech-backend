from django.db import models
from shared.base.models import BaseModel

class TokenUsageLog(BaseModel):
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # If Provider refers to an LLMProvider table in Experience Cloud, use a FK. 
    # If it's just a string like 'OpenAI', use a CharField. I've set it to CharField for flexibility.
    provider = models.CharField(max_length=100) 
    type = models.CharField(max_length=50, null=True, blank=True) # e.g., 'JSON_EXTRACTION', 'TRANSLATION'
    
    # Cross-Boundary Soft Reference
    brand_id = models.IntegerField(null=True, blank=True)
    
    # Metrics
    prompt_tokens = models.IntegerField(default=0)
    completion_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0.00)

    class Meta:
        db_table = 'token_usage_logs'
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['brand_id', 'timestamp']),
        ]


class TokenUsageSummary(BaseModel):
    date = models.DateField()
    provider = models.CharField(max_length=100)
    type = models.CharField(max_length=50, null=True, blank=True)
    
    # Cross-Boundary Soft Reference
    brand_id = models.IntegerField(null=True, blank=True)
    
    # Aggregated Metrics
    requests = models.IntegerField(default=0)
    prompt_tokens = models.IntegerField(default=0)
    completion_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=6, default=0.00)

    class Meta:
        db_table = 'token_usage_summaries'
        constraints = [
            models.UniqueConstraint(
                fields=['date', 'provider', 'type', 'brand_id'], 
                name='unique_token_summary_dimension'
            )
        ]
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['brand_id', 'date']),
        ]