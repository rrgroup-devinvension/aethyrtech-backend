from django.db import models
from core.models import TimeStampedModel, AuditableMixin, SoftDeleteModel

class Platform(SoftDeleteModel, TimeStampedModel, AuditableMixin):
    """Platform model to store quick commerce and marketplace platforms."""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    
    PLATFORM_TYPE_CHOICES = [
        ('quick_commerce', 'Quick Commerce'),
        ('marketplace', 'Marketplace'),
    ]
    
    name = models.CharField(max_length=200, unique=True)
    value = models.CharField(max_length=200, unique=True)
    platform_type = models.CharField(max_length=50, choices=PLATFORM_TYPE_CHOICES)
    api_provider = models.CharField(max_length=200, null=True, blank=True)
    json_configuration = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    class Meta:
        db_table = "platform"
        ordering = ("name",)

    def __str__(self):
        return f"{self.name} ({self.get_platform_type_display()})"
