from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from shared.base.models import BaseModel, TimeStampedModel

class Role(BaseModel):
    ROLE_CHOICES = [
        ('INTERNAL', 'Internal'),
        ('ORGANIZATION', 'Organization'),
    ]
    name = models.CharField(max_length=100)
    role_type = models.CharField(max_length=50, choices=ROLE_CHOICES, null=True, blank=True)
    permissions = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'roles'


class User(AbstractBaseUser, TimeStampedModel):
    USER_TYPE_CHOICES = [
        ('INTERNAL', 'Internal'),
        ('ORGANIZATION', 'Organization'),
    ]
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True)
    password = models.CharField(max_length=255)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']
    
    user_type = models.CharField(max_length=50, choices=USER_TYPE_CHOICES, null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    organization = models.ForeignKey('core_organizations.Organization', on_delete=models.CASCADE, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    managed_organizations = models.ManyToManyField(
        'core_organizations.Organization', 
        through='UserManagedOrganization',
        related_name='managed_by_users'
    )

    class Meta:
        db_table = 'users'


class UserManagedOrganization(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    organization = models.ForeignKey('core_organizations.Organization', on_delete=models.CASCADE)

    class Meta:
        db_table = 'UserManagedOrganizations'
        unique_together = ('user', 'organization')