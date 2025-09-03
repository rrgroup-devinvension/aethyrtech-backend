from django.db import models
from core.models import TimeStampedModel, AuditableMixin, SoftDeleteModel

class Brand(SoftDeleteModel, TimeStampedModel, AuditableMixin):
    name = models.CharField(max_length=150, unique=True)
    logo = models.ImageField(upload_to="brands/logos/", null=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "brand"
        ordering = ("name",)

    def __str__(self):
        return self.name
