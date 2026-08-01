from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.views import APIView


class IsAdminUser(BasePermission):
    """Permission class to allow access only to internal staff or admins."""

    def has_permission(self, request, view: APIView):
        """Check if the user is staff or has an internal role.

        Args:
            request: The incoming HTTP request.
            view: The view that is being accessed.

        Returns:
            bool: True if the user is an admin or internal staff, False otherwise.
        """
        if not request.user:
            return False

        is_staff = getattr(request.user, 'is_staff', False)

        role = getattr(request.user, 'role', None)
        has_internal_role = bool(role and getattr(role, 'role_type', None) == 'INTERNAL')

        return bool(is_staff or has_internal_role)


class IsOwnerOrReadOnly(BasePermission):
    """Permission class to allow editing only to the owner of an object."""

    def has_object_permission(self, request, view, obj):
        """Check if the user owns the object or if the request is read-only.

        Args:
            request (Request): The incoming HTTP request.
            view (APIView): The view that is being accessed.
            obj (Model): The database object being accessed.

        Returns:
            bool: True if the request is read-only or the user is the owner, False otherwise.
        """
        if request.method in SAFE_METHODS:
            return True
        return getattr(obj, "owner", None) == request.user


class HasPermission(BasePermission):
    """Allows access only to users who have a specific application permission.

    Example usage in ViewSet: permission_classes = [HasPermission("CREATE_USER")]
    """

    def __init__(self, required_permission=None):
        """Initialize with an optional required permission."""
        self.required_permission = required_permission

    def __call__(self):
        """Return self to allow instantiation in permission_classes list."""
        return self

    def has_permission(self, request, view):
        """Check if the authenticated user has the required permission.

        Args:
            request (Request): The incoming HTTP request.
            view (APIView): The view that is being accessed.

        Returns:
            bool: True if the user has the required permission, False otherwise.
        """
        if not request.user or not request.user.is_authenticated:
            return False

        # Optional: You can explicitly pass required_permission to the instance,
        # or define `required_permission` on the ViewSet class.
        required = getattr(self, "required_permission", None) or getattr(view, "required_permission", None)

        if not required:
            # If no specific permission is required, default to authenticated
            return True

        # Admin bypass or exact match
        if getattr(request.user, 'is_staff', False):
            return True

        has_perm_func = getattr(request.user, 'has_permission', None)
        return bool(has_perm_func and has_perm_func(required))
