from core.views import BaseViewSet
from .models import User
from .serializers import UserSerializer, UserCreateUpdateSerializer, PasswordUpdateSerializer
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsStaffOrReadOnly
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.response import Response
from apps.brand.serializers import BrandSerializer

class UserViewSet(BaseViewSet):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]
    search_fields = ("name", "email", "role")
    ordering_fields = ("name", "email", "role", "created_at")

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return UserCreateUpdateSerializer
        elif self.action == "set_password":
            return PasswordUpdateSerializer
        return UserSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="set-password")
    def set_password(self, request, pk=None):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data["password"])
        user.save()
        return Response({"detail": "Password updated successfully"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="brands")
    def get_user_brands(self, request):
        user = request.user
        brands = user.brands.all()
        serializer = BrandSerializer(brands, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=["post"], url_path="set-status")
    def set_status(self, request, pk=None):
        user = self.get_object()
        is_active = request.data.get("is_active")
        if is_active is None:
            return Response(
                {"detail": "Please provide 'is_active': true/false in request body."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.is_active = bool(is_active)
        user.save()
        msg = "User activated successfully" if user.is_active else "User deactivated successfully"
        return Response({"detail": msg}, status=status.HTTP_200_OK)