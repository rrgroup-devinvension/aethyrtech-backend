from django.db import models
from core.models import TimeStampedModel, AuditableMixin, SoftDeleteModel

class Category(SoftDeleteModel, TimeStampedModel, AuditableMixin):
    """Category model to organize brands."""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    platform_type = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    class Meta:
        db_table = "category"
        ordering = ("name",)

    def __str__(self):
        return self.name


class CategoryPincode(TimeStampedModel):
    """Association between Category and Pincode."""
    
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='category_pincodes')
    pincode = models.CharField(max_length=10)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "category_pincode"
        unique_together = [['category', 'pincode']]
        ordering = ['category', 'pincode']

    def __str__(self):
        return f"{self.category.name} - {self.pincode}"


class CategoryKeyword(TimeStampedModel):
    """Keywords assigned to a category."""
    
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='category_keywords')
    keyword = models.CharField(max_length=255)
    platform = models.CharField(max_length=255, null=True)
    order = models.IntegerField(null=True, blank=True, default=0)

    class Meta:
        db_table = "category_keyword"
        unique_together = [['category', 'keyword', 'platform']]
        ordering = ['category', 'order', 'keyword']

    def __str__(self):
        return f"{self.category.name} - {self.keyword}- {self.platform}"
