from django.db import models

from shared.base.models import AuditableMixin, BaseModel, SoftDeleteModel


class Organization(AuditableMixin, SoftDeleteModel):
    """Model representing a top-level corporate entity or tenant within the system."""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    status = models.CharField(max_length=50, default='Active')

    class Meta:
        db_table = 'organizations'
        indexes = (
            models.Index(fields=['is_deleted'], name='idx_deleted'),
        )


class Brand(AuditableMixin, SoftDeleteModel):
    """Model representing a distinct brand or product line owned by an Organization."""
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100, blank=True, default='', db_index=True)
    description = models.TextField(blank=True, default='')
    logo = models.CharField(max_length=1024, blank=True, default='')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)
    category = models.ForeignKey('core_categories.Category', on_delete=models.CASCADE, null=True, blank=True)
    aliases = models.CharField(max_length=500, blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'brands'


class Region(SoftDeleteModel):
    """Model representing a geographic or operational region associated with a specific Brand."""
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100, blank=True, default='', db_index=True)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'regions'

class Competitor(BaseModel):
    """Model representing market competitors operating within a specific Region."""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    region = models.ForeignKey(Region, on_delete=models.CASCADE, null=True, blank=True, related_name='competitors')
    aliases = models.CharField(max_length=500, blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'competitors'
