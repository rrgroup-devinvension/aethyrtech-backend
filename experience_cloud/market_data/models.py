
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


class DataImportJob(BaseModel):
    """Tracks background processing and chunked uploads of Excel data."""
    IMPORT_TYPES = (
        ('REVIEWS', 'Reviews'),
        ('DATA_DUMP', 'Data Dump'),
    )
    STATUS_CHOICES = (
        ('UPLOADING', 'Uploading'),
        ('PENDING_PROCESSING', 'Pending Processing'),
        ('PROCESSING', 'Processing'),
        ('PAUSED', 'Paused'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    )

    import_type = models.CharField(max_length=50, choices=IMPORT_TYPES, default='REVIEWS')
    platform = models.CharField(max_length=50, blank=True, default='')
    file = models.FileField(upload_to='imports/', null=True, blank=True)
    file_size_bytes = models.BigIntegerField(default=0, help_text="Total file size uploaded in bytes")
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='UPLOADING')

    # Upload Tracking
    upload_id = models.CharField(max_length=255, blank=True, default='')
    upload_started_at = models.DateTimeField(null=True, blank=True)
    upload_completed_at = models.DateTimeField(null=True, blank=True)
    upload_duration = models.FloatField(null=True, blank=True, help_text="Time taken to upload the file (seconds)")

    # Processing Tracking
    total_rows = models.IntegerField(default=0)
    processed_rows = models.IntegerField(default=0)
    failed_rows = models.IntegerField(default=0)
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processing_completed_at = models.DateTimeField(null=True, blank=True)
    last_processed_at = models.DateTimeField(null=True, blank=True)
    processing_duration = models.FloatField(null=True, blank=True, help_text="Time taken to process the file (seconds)")

    # Errors
    error_message = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'data_import_jobs'
        indexes = [
            models.Index(fields=['status'], name='idx_data_import_status'),
            models.Index(fields=['import_type'], name='idx_data_import_type'),
        ]
