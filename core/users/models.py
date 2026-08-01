from typing import ClassVar

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models

from shared.base.models import BaseModel, TimeStampedModel


class Role(BaseModel):
    """Model representing user roles and their associated permissions."""
    ROLE_CHOICES = (
        ('INTERNAL', 'Internal'),
        ('ORGANIZATION', 'Organization'),
    )
    code = models.CharField(max_length=50, unique=True, blank=True, default='')
    name = models.CharField(max_length=100)
    role_type = models.CharField(max_length=50, choices=ROLE_CHOICES, blank=True, default='')
    permissions = models.JSONField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'roles'

class UserManager(BaseUserManager):
    """Custom manager for the User model to handle creation of regular and super users."""
    def create_user(self, email, password=None, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, TimeStampedModel):
    """Model representing an authenticated user in the system."""
    objects = UserManager()
    USER_TYPE_CHOICES = (
        ('INTERNAL', 'Internal'),
        ('ORGANIZATION', 'Organization'),
    )
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True)
    password = models.CharField(max_length=255)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS: ClassVar[list[str]] = ['name']

    user_type = models.CharField(max_length=50, choices=USER_TYPE_CHOICES, blank=True, default='')
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    extra_permissions = models.JSONField(null=True, blank=True, default=list)
    organization = models.ForeignKey('core_organizations.Organization', on_delete=models.CASCADE, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    brands = models.ManyToManyField('core_organizations.Brand', related_name='users', blank=True)
    regions = models.ManyToManyField('core_organizations.Region', related_name='users', blank=True)

    managed_organizations: models.ManyToManyField = models.ManyToManyField(
        'core_organizations.Organization',
        through='UserManagedOrganization',
        related_name='managed_by_users'
    )

    def get_all_permissions(self):
        """Aggregate and return all permissions assigned to the user via their role and extra permissions."""
        effective_user_type = self.user_type or (self.role.role_type if self.role else None)
        if self.role and self.role.code and self.role.code.upper() == 'ADMIN' and effective_user_type == 'INTERNAL':
            from core.authentication.permissions import PERMISSION_REGISTRY
            return [p["id"] for p in PERMISSION_REGISTRY if 'INTERNAL' in p.get('scopes', [])]

        def _extract_perms(raw):
            if isinstance(raw, dict):
                return [
                    item for sublist in raw.values()
                    for item in (sublist if isinstance(sublist, list) else [sublist])
                ]
            elif isinstance(raw, list):
                return raw
            return [raw] if raw else []

        role_perms = _extract_perms(self.role.permissions if self.role else [])
        extra_perms = _extract_perms(getattr(self, 'extra_permissions', []))
        return list(set(role_perms + extra_perms))

    def has_permission(self, permission):
        """Check if the user possesses a specific permission code."""
        effective_user_type = self.user_type or (self.role.role_type if self.role else None)
        if self.role and self.role.code and self.role.code.upper() == 'ADMIN' and effective_user_type == 'INTERNAL':
            return True
        return permission in self.get_all_permissions()

    class Meta:
        db_table = 'users'


class UserManagedOrganization(BaseModel):
    """Junction model linking a user to organizations they have permission to manage."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    organization = models.ForeignKey('core_organizations.Organization', on_delete=models.CASCADE)

    class Meta:
        db_table = 'user_managed_organizations'
        unique_together = ('user', 'organization')
