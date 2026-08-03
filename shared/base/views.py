from typing import Any, ClassVar, Sequence

from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
import django_filters
import rest_framework.filters


class UUIDLookupMixin:
    """Use UUID as lookup by default; set lookup_field in ViewSets."""
    lookup_field: str = "id"
    lookup_url_kwarg: str | None = "id"

class UserOwnedMixin:
    """Auto-assigns request.user as owner on create; enforces owner-only updates (unless staff).

    Requires model with `owner` FK to settings.AUTH_USER_MODEL.
    """
    owner_field = "owner"

    def perform_create(self: Any, serializer):
        """Set the owner field to the current user upon creation."""
        serializer.save(**{self.owner_field: self.request.user})

    def perform_update(self: Any, serializer):
        """Ensure only the owner or an admin can update the object."""
        instance = self.get_object()
        owner = getattr(instance, self.owner_field, None)
        has_role = hasattr(self.request.user, 'role') and self.request.user.role
        is_internal = has_role and self.request.user.role.role_type == 'INTERNAL'
        is_staff_equivalent = getattr(self.request.user, 'is_staff', False) or is_internal
        if not (self.request.user and (is_staff_equivalent or owner == self.request.user)):
            raise PermissionDenied("You do not have permission to edit this resource.")
        serializer.save()


class BaseViewSet(UUIDLookupMixin, viewsets.ModelViewSet):
    """Standard base ViewSet for all models in Aethyrtech.

    Uses UUID lookup by default.
    Supports dynamic `permission_mapping` and `organization_field` row-level filtering.
    """

    action_permission_mapping: ClassVar[dict[str, str]] = {}
    permission_mapping: ClassVar[dict[str, str]] = {}
    organization_field: str | None = None
    filter_backends: Sequence[Any] = [
        django_filters.rest_framework.DjangoFilterBackend,
        rest_framework.filters.SearchFilter,
        rest_framework.filters.OrderingFilter,
    ]

    def get_permissions(self):
        """Dynamically resolve permissions based on action or method mapping."""
        perms = list(super().get_permissions())

        # Check if the current action has a specifically mapped permission
        action_perm = None
        has_action = hasattr(self, 'action')
        if has_action and getattr(self, 'action', None) in self.action_permission_mapping:
            action_perm = self.action_permission_mapping[self.action]

        if action_perm:
            from shared.permissions import HasPermission
            perms.append(HasPermission(action_perm)())
        # Fallback to general HTTP method mapping
        else:
            method = getattr(self.request, 'method', None)
            if method:
                required_perm = self.permission_mapping.get(str(method))
                if required_perm:
                    from shared.permissions import HasPermission
                    perms.append(HasPermission(required_perm)())

        return perms

    def get_queryset(self):
        """Filter the queryset to only return records belonging to the user's organization."""
        qs = super().get_queryset()
        user = self.request.user

        if not user or not user.is_authenticated:
            return qs.none()

        # Admin or Internal users see everything
        user_role = getattr(user, 'role', None)
        if getattr(user, 'is_staff', False) or (user_role and getattr(user_role, 'role_type', None) == 'INTERNAL'):
            return qs

        # Organization users only see data for their org
        org_field = getattr(self, 'organization_field', None)
        user_org_id = getattr(user, 'organization_id', None)
        if org_field and user_org_id:
            filter_kwargs = {org_field: user_org_id}
            return qs.filter(**filter_kwargs)

        return qs

