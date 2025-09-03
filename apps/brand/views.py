from core.views import BaseViewSet
from .models import Brand
from .serializers import BrandSerializer
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status

class BrandViewSet(BaseViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    search_fields = ("name", "description")
    ordering_fields = ("name", "created_at", "updated_at")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="toggle-status")
    def toggle_status(self, request, pk=None):
        brand = self.get_object()
        is_active = request.data.get("is_active")

        if is_active is None:
            return Response(
                {"detail": "Please provide 'is_active' in request body (true/false)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        brand.is_active = bool(is_active)
        brand.save()
        msg = "Brand activated successfully" if brand.is_active else "Brand deactivated successfully"
        return Response({"detail": msg}, status=status.HTTP_200_OK)