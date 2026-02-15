from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import AuditableMixin, SoftDeleteModel
from apps.brand.models import Brand

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, role="executor", **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        return self.create_user(
            email=email,
            password=password,
            role="admin",
            is_staff=True,
            **extra_fields
        )


class User(AbstractBaseUser, SoftDeleteModel, AuditableMixin):
    """Custom user model with roles, soft delete, and audit fields."""
    class Roles(models.TextChoices):
        ADMIN = "admin", "Admin"
        CTO = "cto", "CTO"
        MARKETING = "marketing", "Marketing"
        EXECUTOR = "executor", "Executor"
        INTERNAL_USER = "internal_user", "Internal User"

    email = models.EmailField(max_length=191, unique=True, db_index=True)
    name = models.CharField(max_length=150, blank=True)
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.EXECUTOR)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    organizations = models.ManyToManyField('brand.Organization', blank=True, related_name='internal_users')
    client_organization = models.ForeignKey('brand.Organization', on_delete=models.SET_NULL, null=True, blank=True, related_name='client_users')    
    brands = models.ManyToManyField("brand.Brand", blank=True, related_name="users")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = "user"

    def __str__(self):
        return self.email

    def can_access_brand(self, brand_id):
        """Check if user can access a specific brand."""
        if self.role == self.Roles.ADMIN:
            return True
        if self.role == self.Roles.INTERNAL_USER:
            # Internal users can access brands in their assigned organizations
            return Brand.objects.filter(
                id=brand_id,
                organization__in=self.organizations.all()
            ).exists()
        # Client users can only access their assigned brands
        return self.brands.filter(id=brand_id).exists()
    
    def can_manage_organization(self, organization_id):
        """Check if user can manage a specific organization."""
        if self.role == self.Roles.ADMIN:
            return True
        if self.role == self.Roles.INTERNAL_USER:
            return self.organizations.filter(id=organization_id).exists()
        return False
