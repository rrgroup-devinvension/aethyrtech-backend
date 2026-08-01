from django.db import models

from shared.base.models import BaseModel


class Category(BaseModel):
    """Model representing a content or data category.

    Categories are used to group related entities across the system.
    """
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    )
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    class Meta:
        db_table = 'categories'
        ordering = ("name",)

    def __str__(self):
        """Return the category's name as its string representation."""
        return self.name


