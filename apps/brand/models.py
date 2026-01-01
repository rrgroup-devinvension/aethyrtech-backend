from django.db import models
from core.models import TimeStampedModel, AuditableMixin, SoftDeleteModel

class Brand(SoftDeleteModel, TimeStampedModel, AuditableMixin):
    class BrandTypes(models.TextChoices):
        MARKETPLACE = "marketplace", "Marketplace"
        QUICK_COMMERCE = "quick_commerce", "Quick Commerce"
    
    name = models.CharField(max_length=150, unique=True)
    logo = models.ImageField(upload_to="brands/logos/", null=True, blank=True)
    description = models.TextField(blank=True)
    brand_type = models.CharField(max_length=20, choices=BrandTypes.choices, default=BrandTypes.MARKETPLACE)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "brand"
        ordering = ("name",)

    def __str__(self):
        return self.name
