from typing import Optional, Iterable
from django.db import models
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

# ===========================
# Base QuerySets & Managers
# ===========================

class BaseQuerySet(models.QuerySet):
    """Common queryset helpers for all models."""
    def ids(self) -> Iterable:
        return self.values_list("id", flat=True)

    def updated_since(self, dt):
        return self.filter(updated_at__gte=dt)

    def created_since(self, dt):
        return self.filter(created_at__gte=dt)


class BaseManager(models.Manager.from_queryset(BaseQuerySet)):
    """Manager using BaseQuerySet"""
    pass


class SoftDeleteQuerySet(BaseQuerySet):
    """QuerySet that supports soft delete."""
    def delete(self):
        return super().update(is_deleted=True, deleted_at=timezone.now())

    def alive(self):
        return self.filter(is_deleted=False)

    def dead(self):
        return self.filter(is_deleted=True)


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Manager for soft-deletable models."""
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


# ===========================
# Base Models
# ===========================

class TimeStampedModel(models.Model):
    """Adds created_at and updated_at fields."""
    created_at = models.DateTimeField(db_index=True, default=timezone.now, editable=False)
    updated_at = models.DateTimeField(db_index=True, auto_now=True)

    class Meta:
        abstract = True


class AuditableMixin(models.Model):
    """Tracks the user who created/updated the record."""
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_%(class)s_set"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_%(class)s_set"
    )

    class Meta:
        abstract = True


class BaseModel(TimeStampedModel):
    """Base model with AutoField primary key."""
    id = models.AutoField(primary_key=True)
    objects = BaseManager()

    class Meta:
        abstract = True


class SoftDeleteModel(BaseModel):
    """Base model supporting soft delete."""
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_with_deleted = SoftDeleteQuerySet.as_manager()

    class Meta:
        abstract = True

    def delete(self, using: Optional[str] = None, keep_parents: bool = False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])


class StatusMixin(models.Model):
    """Reusable status field pattern."""
    STATUSES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("archived", "Archived"),
    ]
    status = models.CharField(max_length=32, choices=STATUSES, default="draft", db_index=True)

    class Meta:
        abstract = True


