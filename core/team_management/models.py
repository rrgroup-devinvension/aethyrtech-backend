from django.db import models
from shared.base.models import BaseModel
from core.organizations.models import Brand

class TeamMember(BaseModel):
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='team_members')
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=255, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    mobile = models.CharField(max_length=50, blank=True, default='')

    class Meta:
        db_table = 'team_members'
