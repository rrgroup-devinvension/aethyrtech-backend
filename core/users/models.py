from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from shared.base.models import BaseModel, TimeStampedModel

class Role(BaseModel):
    ROLE_CHOICES = [
        ('INTERNAL', 'Internal'),
        ('ORGANIZATION', 'Organization'),
    ]
    code = models.CharField(max_length=50, unique=True, null=True)
    name = models.CharField(max_length=100)
    role_type = models.CharField(max_length=50, choices=ROLE_CHOICES, null=True, blank=True)
    permissions = models.JSONField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'roles'

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, TimeStampedModel):
    objects = UserManager()
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
    extra_permissions = models.JSONField(null=True, blank=True, default=list)
    organization = models.ForeignKey('core_organizations.Organization', on_delete=models.CASCADE, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    managed_organizations = models.ManyToManyField(
        'core_organizations.Organization', 
        through='UserManagedOrganization',
        related_name='managed_by_users'
    )

    def get_all_permissions(self):
        if self.role and self.role.code and self.role.code.upper() == 'ADMIN':
            from core.authentication.permissions import PERMISSION_REGISTRY
            return [p["id"] for p in PERMISSION_REGISTRY]
        
        def _extract_perms(raw):
            if isinstance(raw, dict): return [item for sublist in raw.values() for item in (sublist if isinstance(sublist, list) else [sublist])]
            elif isinstance(raw, list): return raw
            return [raw] if raw else []
            
        role_perms = _extract_perms(self.role.permissions if self.role else [])
        extra_perms = _extract_perms(getattr(self, 'extra_permissions', []))
        return list(set(role_perms + extra_perms))

    def has_permission(self, permission):
        if self.role and self.role.code and self.role.code.upper() == 'ADMIN':
            return True
        return permission in self.get_all_permissions()

    class Meta:
        db_table = 'users'


class UserManagedOrganization(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    organization = models.ForeignKey('core_organizations.Organization', on_delete=models.CASCADE)

    class Meta:
        db_table = 'user_managed_organizations'
        unique_together = ('user', 'organization')