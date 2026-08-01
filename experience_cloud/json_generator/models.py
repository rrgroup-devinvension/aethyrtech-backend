from typing import ClassVar

from django.db import models

from shared.base.models import BaseModel


class JsonTemplate(BaseModel):
    """Model representing a configuration template for generating JSON or CSV payload files."""
    PROCESS_CHOICES: ClassVar[tuple] = (('automatic', 'Automatic'), ('manual', 'Manual'))
    FORMAT_CHOICES: ClassVar[tuple] = (('csv', 'CSV'), ('json', 'JSON'))

    name = models.CharField(max_length=255)
    template = models.CharField(max_length=255, unique=True)
    process_type = models.CharField(max_length=50, choices=PROCESS_CHOICES, blank=True, default='')
    format = models.CharField(max_length=50, choices=FORMAT_CHOICES, blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'json_templates'

class RegionJsonFile(BaseModel):
    """Model tracking the generation status and storage metadata of a specific Region's payload file."""
    region = models.ForeignKey('core_organizations.Region', on_delete=models.CASCADE)
    template = models.ForeignKey(JsonTemplate, on_delete=models.CASCADE)
    file_name = models.CharField(max_length=1024, blank=True, default='')
    file_path = models.CharField(max_length=2048, blank=True, default='')
    file_size = models.BigIntegerField(null=True, blank=True)
    checksum = models.CharField(max_length=255, blank=True, default='')
    generation_duration = models.FloatField(null=True, blank=True)
    products_processed = models.IntegerField(null=True, blank=True)
    last_generated_at = models.DateTimeField(null=True, blank=True)
    task_id = models.CharField(max_length=255, blank=True, default='')
    status = models.CharField(max_length=50, blank=True, default='')
    error_message = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'region_json_files'
