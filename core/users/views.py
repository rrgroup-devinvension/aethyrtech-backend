from core.authentication.permissions import AppPermissions
import logging
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from shared.base.views import BaseViewSet

from .models import User, Role
from .serializers import (
    UserSerializer, 
    UserCreateUpdateSerializer, 
    PasswordUpdateSerializer,
    ProfileSerializer,
    ProfileUpdateSerializer,
    ChangePasswordSerializer,
    OrganizationMinimalSerializer,
    RoleSerializer,
    UserBrandRegionSerializer
)

logger = logging.getLogger(__name__)

@extend_schema_view(
    list=extend_schema(summary="List Roles"),
    retrieve=extend_schema(summary="Get Role")
)
class RoleViewSet(BaseViewSet):
    organization_field = None
    permission_mapping = {
        'GET': AppPermissions.READ_ROLES,
        'POST': AppPermissions.CREATE_ROLE,
        'PUT': AppPermissions.UPDATE_ROLE,
        'PATCH': AppPermissions.UPDATE_ROLE,
        'DELETE': AppPermissions.DELETE_ROLE
    }
    queryset = Role.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = RoleSerializer
    search_fields = ("name", "code")
    ordering_fields = ("name", "code")
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']

    @extend_schema(summary="Get Permission Registry", responses={200: list})
    @action(detail=False, methods=["get"], url_path="permissions")
    def list_permissions(self, request):
        from core.authentication.permissions import PERMISSION_REGISTRY
        logger.info("Fetching permission registry")
        return Response(PERMISSION_REGISTRY, status=status.HTTP_200_OK)

    @extend_schema(summary="Set Role Status")
    @action(detail=True, methods=["post"], url_path="set-status")
    def set_status(self, request, pk=None):
        role = self.get_object()
        is_active = request.data.get("is_active")
        if is_active is not None:
            role.is_active = is_active
            role.save()
        serializer = self.get_serializer(role)
        return Response(serializer.data, status=status.HTTP_200_OK)

@extend_schema_view(
    list=extend_schema(summary="List Users"),
    retrieve=extend_schema(summary="Get User"),
    create=extend_schema(summary="Create User"),
    update=extend_schema(summary="Update User"),
    partial_update=extend_schema(summary="Partial Update User"),
    destroy=extend_schema(summary="Delete User")
)
class UserViewSet(BaseViewSet):
    action_permission_mapping = {
        'set_status': AppPermissions.UPDATE_USER,
        'set_password': AppPermissions.UPDATE_USER,
    }

    organization_field = 'organization_id'
    permission_mapping = {
        'GET': AppPermissions.READ_USER,
        'POST': AppPermissions.CREATE_USER,
        'PUT': AppPermissions.UPDATE_USER,
        'PATCH': AppPermissions.UPDATE_USER,
        'DELETE': AppPermissions.DELETE_USER
    }
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]
    search_fields = ("name", "email", "role")
    ordering_fields = ("name", "email", "role", "created_at")

    def get_permissions(self):
        if self.action in ['get_user_brands', 'get_user_organizations']:
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return UserCreateUpdateSerializer
        elif self.action == "set_password":
            return PasswordUpdateSerializer
        return UserSerializer

    @extend_schema(summary="Set Password", request=PasswordUpdateSerializer, responses={200: dict})
    @action(detail=True, methods=["post"], url_path="set-password")
    def set_password(self, request, id=None):
        logger.info(f"Setting password for user id {id}")
        user = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data["password"])
        user.save()
        logger.info(f"Password updated successfully for user id {id}")
        return Response({"detail": "Password updated successfully"}, status=status.HTTP_200_OK)

    @extend_schema(summary="Get User Organizations", responses={200: OrganizationMinimalSerializer(many=True)})
    @action(detail=False, methods=["get"], url_path="organizations")
    def get_user_organizations(self, request):
        user = request.user
        logger.info(f"Fetching organizations for user id {user.id}")
        orgs = user.managed_organizations.all()
        serializer = OrganizationMinimalSerializer(orgs, many=True)
        return Response(serializer.data)

    @extend_schema(summary="Get User Brands and Regions", responses={200: UserBrandRegionSerializer(many=True)})
    @action(detail=False, methods=["get"], url_path="brands")
    def get_user_brands(self, request):
        user = request.user
        from core.organizations.models import Brand
        logger.info(f"Fetching brands and regions for user id {user.id}")

        effective_user_type = user.user_type or (user.role.role_type if user.role else None)

        if effective_user_type == 'ORGANIZATION' and user.organization:
            brands = Brand.objects.filter(organization=user.organization, is_active=True, is_deleted=False)
        else:
            # Internal user or unassigned organization - return all active brands for testing
            brands = Brand.objects.filter(is_active=True, is_deleted=False)

        serializer = UserBrandRegionSerializer(brands, many=True)
        return Response(serializer.data)
    
    @extend_schema(summary="Set User Status", request=dict, responses={200: dict})
    @action(detail=True, methods=["post"], url_path="set-status")
    def set_status(self, request, id=None):
        logger.info(f"Setting status for user id {id}")
        user = self.get_object()
        is_active = request.data.get("is_active")
        if is_active is None:
            logger.warning(f"set_status called without 'is_active' for user id {id}")
            return Response(
                {"detail": "Please provide 'is_active': true/false in request body."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.is_active = bool(is_active)
        user.save()
        msg = "User activated successfully" if user.is_active else "User deactivated successfully"
        logger.info(f"User id {id} status set to {user.is_active}")
        return Response({"detail": msg}, status=status.HTTP_200_OK)


class ProfileView(APIView):
    """Get and update user profile"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(summary="Get Current User Profile", responses={200: ProfileSerializer})
    def get(self, request):
        """Get current user's profile"""
        serializer = ProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @extend_schema(summary="Update Current User Profile", request=ProfileUpdateSerializer, responses={200: ProfileSerializer})
    def put(self, request):
        """Update current user's profile"""
        logger.info(f"Updating profile for user id {request.user.id}")
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Return full profile
        response_serializer = ProfileSerializer(request.user)
        logger.info(f"Profile updated successfully for user id {request.user.id}")
        return Response(response_serializer.data, status=status.HTTP_200_OK)
    
    @extend_schema(summary="Partially Update Current User Profile", request=ProfileUpdateSerializer, responses={200: ProfileSerializer})
    def patch(self, request):
        """Partially update current user's profile"""
        return self.put(request)


class ChangePasswordView(APIView):
    """Change password for authenticated user"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(summary="Change Password", request=ChangePasswordSerializer, responses={200: dict})
    def post(self, request):
        logger.info(f"Changing password for user id {request.user.id}")
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        # Update password
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        logger.info(f"Password changed successfully for user id {request.user.id}")
        return Response(
            {"detail": "Password changed successfully"},
            status=status.HTTP_200_OK
        )
