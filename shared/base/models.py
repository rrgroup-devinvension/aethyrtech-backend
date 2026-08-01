from collections.abc import Iterable
from typing import ClassVar

from django.conf import settings
from django.db import models
from django.utils import timezone

# ===========================
# Base QuerySets & Managers
# ===========================

class BaseQuerySet(models.QuerySet):
    """Common queryset helpers for all models."""
    def ids(self) -> Iterable:
        """Return an iterable of IDs."""
        return self.values_list("id", flat=True)

    def updated_since(self, dt):
        """Filter records updated since a datetime."""
        return self.filter(updated_at__gte=dt)

    def created_since(self, dt):
        """Filter records created since a datetime."""
        return self.filter(created_at__gte=dt)

class BaseManager(models.Manager.from_queryset(BaseQuerySet)):  # type: ignore
    """Manager using BaseQuerySet."""
    pass

class SoftDeleteQuerySet(BaseQuerySet):
    """QuerySet that supports soft delete."""
    def delete(self) -> tuple[int, dict[str, int]]:
        """Soft delete the records in the queryset."""
        count = super().update(is_deleted=True, deleted_at=timezone.now())
        return (count, {self.model._meta.label: count})

    def alive(self):
        """Filter out soft-deleted records."""
        return self.filter(is_deleted=False)

    def dead(self):
        """Filter for only soft-deleted records."""
        return self.filter(is_deleted=True)

class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):  # type: ignore
    """Manager for soft-deletable models."""
    def get_queryset(self):
        """Return only alive records by default."""
        return super().get_queryset().filter(is_deleted=False)

# ===========================
# Base Models
# ===========================

class TimeStampedModel(models.Model):
    """Adds created_at and updated_at fields."""
    created_at = models.DateTimeField(db_index=True, default=timezone.now, editable=False)
    updated_at = models.DateTimeField(db_index=True, auto_now=True)

    class Meta:  # type: ignore
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

    class Meta:  # type: ignore
        abstract = True

class BaseModel(TimeStampedModel):
    """Base model with BigAutoField primary key."""
    id = models.BigAutoField(primary_key=True)
    objects: ClassVar[BaseManager] = BaseManager()

    class Meta(TimeStampedModel.Meta):  # type: ignore
        abstract = True

class SoftDeleteModel(BaseModel):
    """Base model supporting soft delete."""
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects: ClassVar[SoftDeleteManager] = SoftDeleteManager()
    all_with_deleted: ClassVar[models.Manager] = models.Manager()  # type: ignore[no-redef]

    class Meta(BaseModel.Meta):  # type: ignore
        abstract = True

    def delete(self, using: str | None = None, keep_parents: bool = False) -> tuple[int, dict[str, int]]:
        """Soft delete the instance."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])
        return (1, {self._meta.label: 1})

class StatusMixin(models.Model):
    """Reusable status field pattern."""

    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("active", "Active"),
        ("archived", "Archived"),
    )

    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="draft", db_index=True)

    class Meta:  # type: ignore
        abstract = True
