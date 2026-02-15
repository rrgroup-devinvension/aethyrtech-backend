from core.views import BaseViewSet
from .models import Brand, Organization, Competitor
from .serializers import BrandSerializer, OrganizationSerializer, CompetitorSerializer
from apps.scheduler.utility.service_utility import ensure_brand_json_files
from apps.scheduler.enums import JsonTemplate
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status


class OrganizationViewSet(BaseViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    search_fields = ('name', 'description')
    ordering_fields = ('name', 'status', 'created_at', 'updated_at')

    def perform_create(self, serializer):
        brand = serializer.save(created_by=self.request.user)
        # Ensure BrandJsonFile entries exist for new brand
        try:
            ensure_brand_json_files(brand, [t.slug for t in JsonTemplate])
        except Exception:
            # Don't block brand creation on provisioning failures; log via service layer when available
            pass

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=['get'], url_path='brands')
    def organization_brands(self, request, pk=None):
        organization = self.get_object()
        brands = organization.brands.filter(is_deleted=False)
        page = self.paginate_queryset(brands)
        if page is not None:
            serializer = BrandSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = BrandSerializer(brands, many=True)
        return Response(serializer.data)


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
    
    @action(detail=False, methods=["get"], url_path="active")
    def list_active(self, request):
        active_brands = self.get_queryset().filter(is_active=True)
        page = self.paginate_queryset(active_brands)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(active_brands, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CompetitorViewSet(BaseViewSet):
    queryset = Competitor.objects.all()
    serializer_class = CompetitorSerializer
    search_fields = ("name", "description")
    ordering_fields = ("name", "created_at", "updated_at")

    def get_queryset(self):
        queryset = super().get_queryset()
        brand_id = self.request.query_params.get('brand')
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)
        return queryset