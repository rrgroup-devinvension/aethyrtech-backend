from django.db import models

from core.organizations.models import Brand
from shared.base.models import BaseModel


class TeamMember(BaseModel):
    """Team member model."""
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='team_members')
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=255, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    mobile = models.CharField(max_length=50, blank=True, default='')

    class Meta:
        db_table = 'team_members'
