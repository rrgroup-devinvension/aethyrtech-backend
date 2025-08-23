from core.views import BaseViewSet
from .models import User
from .serializers import UserSerializer, UserCreateUpdateSerializer
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsStaffOrReadOnly

class UserViewSet(BaseViewSet):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]
    search_fields = ("name", "email", "role")
    ordering_fields = ("name", "email", "role", "created_at")

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return UserCreateUpdateSerializer
        return UserSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
