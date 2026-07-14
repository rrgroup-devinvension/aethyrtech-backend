from django.db import models
from shared.base.models import BaseModel

class JsonTemplate(BaseModel):
    PROCESS_CHOICES = [('automatic', 'Automatic'), ('manual', 'Manual')]
    FORMAT_CHOICES = [('csv', 'CSV'), ('json', 'JSON')]
    
    name = models.CharField(max_length=255)
    template = models.CharField(max_length=255, unique=True)
    process_type = models.CharField(max_length=50, choices=PROCESS_CHOICES, null=True, blank=True)
    format = models.CharField(max_length=50, choices=FORMAT_CHOICES, null=True, blank=True)

    class Meta:
        db_table = 'json_templates'

class RegionJsonFile(BaseModel):
    region = models.ForeignKey('core_organizations.Region', on_delete=models.CASCADE)
    template = models.ForeignKey(JsonTemplate, on_delete=models.CASCADE)
    file_name = models.CharField(max_length=1024, null=True, blank=True)
    file_path = models.CharField(max_length=2048, null=True, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    checksum = models.CharField(max_length=255, null=True, blank=True)
    generation_duration = models.FloatField(null=True, blank=True)
    last_generated_at = models.DateTimeField(null=True, blank=True)
    task = models.ForeignKey('experience_cloud_executions.JsonFileTask', on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_files')

    class Meta:
        db_table = 'region_json_files'

