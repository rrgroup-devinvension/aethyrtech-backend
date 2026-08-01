
# ruff: noqa: DJ001, RUF012
from django.db import models

from shared.base.models import BaseModel


class ApiDump(BaseModel):
    """Tracks metadata and execution stats for data dumps."""
    task_id = models.CharField(max_length=255, null=True, blank=True)
    keyword_name = models.CharField(max_length=255, null=True, blank=True)
    location_name = models.CharField(max_length=255, null=True, blank=True)
    platform = models.ForeignKey('experience_cloud_catalog.Platform', on_delete=models.SET_NULL, null=True, blank=True)
    category_id = models.IntegerField(null=True, blank=True)
    api_provider = models.ForeignKey(
        'experience_cloud_api_provider.ApiProvider', on_delete=models.SET_NULL, null=True, blank=True
    )
    product_count = models.IntegerField(default=0)
    products_found = models.IntegerField(default=0)
    response_time = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)

    # Regional Tracking (JSON lists of ids and names)
    region_ids = models.JSONField(default=list)
    region_names = models.JSONField(default=list)

    class Meta:
        db_table = 'api_dumps'
        indexes = [
            models.Index(fields=['keyword_name', 'location_name', 'created_at'], name='idx_api_dump_lookup'),
        ]
