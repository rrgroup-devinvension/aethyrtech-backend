from django.db import models
from shared.base.models import BaseModel, SoftDeleteModel, AuditableMixin

class Organization(AuditableMixin, SoftDeleteModel):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=50, default='Active')

    class Meta:
        db_table = 'organizations'
        indexes = [
            models.Index(fields=['is_deleted'], name='idx_deleted'),
        ]


class Brand(AuditableMixin, SoftDeleteModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    description = models.TextField(null=True, blank=True)
    logo = models.CharField(max_length=1024, null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)
    category = models.ForeignKey('core_categories.Category', on_delete=models.CASCADE, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'brands'


class Region(SoftDeleteModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)

    class Meta:
        db_table = 'regions'

class Competitor(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, null=True, blank=True, related_name='competitors')

    class Meta:
        db_table = 'competitors'
