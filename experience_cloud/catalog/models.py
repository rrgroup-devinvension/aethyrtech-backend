from django.db import models

from shared.base.models import BaseModel


class Platform(BaseModel):
    """Model representing an e-commerce or external platform (e.g., Amazon, Flipkart) where products are listed."""
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100, unique=True, blank=True, default='', db_index=True)
    platform_type = models.CharField(max_length=100, blank=True, default='')
    api_provider = models.ForeignKey(
        'experience_cloud_api_provider.ApiProvider',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='platforms'
    )
    configuration = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=50, default='Active')

    class Meta:
        db_table = 'platforms'



class Location(BaseModel):
    """Model representing a specific geographic region or pincode configured for localized catalog tracking."""
    pincode = models.CharField(max_length=50, null=True, blank=True)  # noqa: DJ001
    address = models.CharField(max_length=255, null=True, blank=True)  # noqa: DJ001
    lat = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    lng = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    region = models.ForeignKey('core_organizations.Region', on_delete=models.CASCADE)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    category = models.ForeignKey('core_categories.Category', on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'locations'
        constraints = (
            models.UniqueConstraint(
                fields=['region', 'platform', 'category', 'pincode', 'address'],
                name='unique_location_combo'
            ),
        )
        indexes = (
            models.Index(fields=['region', 'platform'], name='idx_location_region_platform'),
        )

class Keyword(BaseModel):
    """Model representing SEO search keywords targeted for scraping and tracking on specific platforms."""
    keyword = models.CharField(max_length=255)
    category = models.ForeignKey('core_categories.Category', on_delete=models.CASCADE, null=True, blank=True)
    region = models.ForeignKey('core_organizations.Region', on_delete=models.CASCADE)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'keywords'
        constraints = (
            models.UniqueConstraint(fields=['region', 'platform', 'category', 'keyword'], name='unique_keyword_combo'),
        )
        indexes = (
            models.Index(fields=['region', 'platform'], name='idx_keyword_region_platform'),
        )
