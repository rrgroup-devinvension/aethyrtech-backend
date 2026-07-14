from django.db import models
from shared.base.models import BaseModel

class APIUsageLog(BaseModel):
    # Time and Status
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50)  # e.g., 'SUCCESS', 'FAILED', 'TIMEOUT'
    
    # Internal Foreign Keys (References to other Experience Cloud models)
    # Replace 'app_name' with the actual app where these live, e.g., 'data_dump.ApiProvider'
    api_provider = models.ForeignKey('experience_cloud_api_provider.ApiProvider', on_delete=models.SET_NULL, null=True, blank=True)
    platform = models.ForeignKey('experience_cloud_catalog.Platform', on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ForeignKey('core_categories.Category', on_delete=models.SET_NULL, null=True, blank=True)
    keyword = models.ForeignKey('experience_cloud_catalog.Keyword', on_delete=models.SET_NULL, null=True, blank=True)
    location = models.ForeignKey('experience_cloud_catalog.Location', on_delete=models.SET_NULL, null=True, blank=True) # Previously Pincode
    
    # Cross-Boundary Soft References (References to Core Foundation)
    brand_id = models.IntegerField(null=True, blank=True)
    region_id = models.IntegerField(null=True, blank=True)
    
    # Metrics
    response_time = models.FloatField(null=True, blank=True) # In milliseconds or seconds
    cost = models.DecimalField(max_digits=10, decimal_places=6, default=0.00)
    request_size = models.IntegerField(null=True, blank=True, help_text="Size in bytes")
    response_size = models.IntegerField(null=True, blank=True, help_text="Size in bytes")

    class Meta:
        db_table = 'APIUsageLogs'
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['brand_id', 'timestamp']),
            models.Index(fields=['api_provider', 'status']),
        ]


class APIUsageSummary(BaseModel):
    date = models.DateField()
    
    # Internal Foreign Keys
    api_provider = models.ForeignKey('experience_cloud_api_provider.ApiProvider', on_delete=models.CASCADE)
    platform = models.ForeignKey('experience_cloud_catalog.Platform', on_delete=models.CASCADE)
    
    # Cross-Boundary Soft References
    brand_id = models.IntegerField(null=True, blank=True)
    region_id = models.IntegerField(null=True, blank=True)
    
    # Aggregated Metrics
    total_calls = models.IntegerField(default=0)
    success_calls = models.IntegerField(default=0)
    failed_calls = models.IntegerField(default=0)
    average_response_time = models.FloatField(default=0.0)
    total_products = models.IntegerField(default=0)
    total_cost = models.DecimalField(max_digits=12, decimal_places=6, default=0.00)

    class Meta:
        db_table = 'APIUsageSummaries'
        # Unique constraint ensures we only have one summary row per dimension combination per day
        constraints = [
            models.UniqueConstraint(
                fields=['date', 'api_provider', 'platform', 'brand_id', 'region_id'], 
                name='unique_api_summary_dimension'
            )
        ]
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['brand_id', 'date']),
        ]

