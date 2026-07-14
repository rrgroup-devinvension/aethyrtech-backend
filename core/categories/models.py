from django.db import models
from shared.base.models import BaseModel

class Category(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'categories'