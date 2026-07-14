from django.db import models
from shared.base.models import BaseModel

class ApiProvider(BaseModel):
    name = models.CharField(max_length=100, null=True, blank=True)
    base_url = models.CharField(max_length=500, null=True, blank=True)
    headers = models.JSONField(null=True, blank=True)
    authentication = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=50, default='Active')

    class Meta:
        db_table = 'api_providers'