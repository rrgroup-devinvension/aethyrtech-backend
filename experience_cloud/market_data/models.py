from django.db import models
from shared.base.models import BaseModel
import uuid


class ApiDump(BaseModel):
    task_id = models.CharField(max_length=255, null=True, blank=True)
    keyword = models.ForeignKey('experience_cloud_catalog.Keyword', on_delete=models.SET_NULL, null=True, blank=True)
    platform = models.ForeignKey('experience_cloud_catalog.Platform', on_delete=models.SET_NULL, null=True, blank=True)
    location = models.ForeignKey('experience_cloud_catalog.Location', on_delete=models.SET_NULL, null=True, blank=True)
    api_provider = models.ForeignKey('experience_cloud_api_provider.ApiProvider', on_delete=models.SET_NULL, null=True, blank=True)
    product_count = models.IntegerField(default=0)
    products_found = models.IntegerField(default=0)
    response_time = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'api_dumps'
        indexes = [
            models.Index(fields=['keyword', 'location', 'created_at'], name='idx_api_dump_lookup'),
        ]
