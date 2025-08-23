from django.conf import settings
from django.utils.functional import cached_property
from rest_framework.exceptions import PermissionDenied


class UUIDLookupMixin:
    """
    Use UUID as lookup by default; set lookup_field in ViewSets.
    """
    lookup_field = "id"
    lookup_url_kwarg = "id"


class UserOwnedMixin:
    """
    Auto-assigns request.user as owner on create; enforces owner-only updates (unless staff).
    Requires model with `owner` FK to settings.AUTH_USER_MODEL.
    """
    owner_field = "owner"

    def perform_create(self, serializer):
        serializer.save(**{self.owner_field: self.request.user})

    def perform_update(self, serializer):
        instance = self.get_object()
        owner = getattr(instance, self.owner_field, None)
        if not (self.request.user and (self.request.user.is_staff or owner == self.request.user)):
            raise PermissionDenied("You do not have permission to edit this resource.")
        serializer.save()
