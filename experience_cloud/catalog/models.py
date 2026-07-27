from django.db import models
from shared.base.models import BaseModel

class Platform(BaseModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100, unique=True, null=True, blank=True, db_index=True)
    platform_type = models.CharField(max_length=100, null=True, blank=True)
    api_provider = models.ForeignKey('experience_cloud_api_provider.ApiProvider', on_delete=models.SET_NULL, null=True, blank=True, related_name='platforms')
    configuration = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=50, default='Active')

    class Meta:
        db_table = 'platforms'



class Location(BaseModel):
    pincode = models.CharField(max_length=50, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    lat = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    lng = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    region = models.ForeignKey('core_organizations.Region', on_delete=models.CASCADE)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    category = models.ForeignKey('core_categories.Category', on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'locations'
        constraints = [
            models.UniqueConstraint(fields=['region', 'platform', 'category', 'pincode'], name='unique_location_combo')
        ]
        indexes = [
            models.Index(fields=['region', 'platform'], name='idx_location_region_platform'),
        ]

class Keyword(BaseModel):
    keyword = models.CharField(max_length=255)
    category = models.ForeignKey('core_categories.Category', on_delete=models.CASCADE, null=True, blank=True)
    region = models.ForeignKey('core_organizations.Region', on_delete=models.CASCADE)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'keywords'
        constraints = [
            models.UniqueConstraint(fields=['region', 'platform', 'category', 'keyword'], name='unique_keyword_combo')
        ]
        indexes = [
            models.Index(fields=['region', 'platform'], name='idx_keyword_region_platform'),
        ]
