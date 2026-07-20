from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)

class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return getattr(obj, "owner", None) == request.user

class HasPermission(BasePermission):
    """
    Allows access only to users who have a specific application permission.
    Example usage in ViewSet: permission_classes = [HasPermission("CREATE_USER")]
    """
    def __init__(self, required_permission=None):
        self.required_permission = required_permission

    def __call__(self):
        return self

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Optional: You can explicitly pass required_permission to the instance,
        # or define `required_permission` on the ViewSet class.
        required = getattr(self, "required_permission", None) or getattr(view, "required_permission", None)
        
        if not required:
            # If no specific permission is required, default to authenticated
            return True
            
        # Admin bypass or exact match
        if request.user.is_staff:
            return True
            
        return request.user.has_permission(required)
