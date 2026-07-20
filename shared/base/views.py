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

from rest_framework import viewsets

class BaseViewSet(UUIDLookupMixin, viewsets.ModelViewSet):
    """
    Standard base ViewSet for all models in Aethyrtech.
    Uses UUID lookup by default.
    Supports dynamic `permission_mapping` and `organization_field` row-level filtering.
    """
    
    def get_permissions(self):
        perms = super().get_permissions()
        
        # Check if the current action has a specifically mapped permission
        action_perm = None
        if hasattr(self, 'action_permission_mapping') and hasattr(self, 'action') and self.action in self.action_permission_mapping:
            action_perm = self.action_permission_mapping[self.action]
            
        if action_perm:
            from shared.permissions import HasPermission
            perms.append(HasPermission(action_perm)())
        # Fallback to general HTTP method mapping
        elif hasattr(self, 'permission_mapping'):
            required_perm = self.permission_mapping.get(self.request.method)
            if required_perm:
                from shared.permissions import HasPermission
                perms.append(HasPermission(required_perm)())
                
        return perms

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return qs.none()
            
        # Admin or Internal users see everything
        if user.is_staff or (user.role and user.role.role_type == 'INTERNAL'):
            return qs
            
        # Organization users only see data for their org
        org_field = getattr(self, 'organization_field', None)
        if org_field and user.organization_id:
            filter_kwargs = {org_field: user.organization_id}
            return qs.filter(**filter_kwargs)
            
        return qs

