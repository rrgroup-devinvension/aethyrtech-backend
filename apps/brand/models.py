from django.db import models
from core.models import TimeStampedModel, AuditableMixin, SoftDeleteModel
from django.db.models import JSONField


class Organization(SoftDeleteModel, TimeStampedModel, AuditableMixin):
    """Organization model to group brands."""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    class Meta:
        db_table = "organization"
        ordering = ("name",)

    def __str__(self):
        return self.name

class Brand(SoftDeleteModel, TimeStampedModel, AuditableMixin):
    class BrandTypes(models.TextChoices):
        MARKETPLACE = "marketplace", "Marketplace"
        QUICK_COMMERCE = "quick_commerce", "Quick Commerce"
    
    name = models.CharField(max_length=150, unique=True)
    logo = models.ImageField(upload_to="brands/logos/", null=True, blank=True)
    description = models.TextField(blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name='brands')
    category = models.ForeignKey('category.Category', on_delete=models.SET_NULL, null=True, blank=True, related_name='brands')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "brand"
        ordering = ("name",)

    def __str__(self):
        return self.name


class Competitor(SoftDeleteModel, TimeStampedModel):
    """Competitor model for brands."""
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='competitors')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "competitor"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.name} (Competitor of {self.brand.name})"
