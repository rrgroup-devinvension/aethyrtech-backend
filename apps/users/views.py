from core.views import BaseViewSet
from .models import User
from .serializers import UserSerializer, UserCreateUpdateSerializer, PasswordUpdateSerializer
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsStaffOrReadOnly
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.response import Response

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
