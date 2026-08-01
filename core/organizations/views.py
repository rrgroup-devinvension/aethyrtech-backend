import logging
from typing import ClassVar

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.authentication.permissions import AppPermissions
from shared.base.views import BaseViewSet

from .models import Brand, Competitor, Organization, Region
from .serializers import BrandSerializer, CompetitorSerializer, OrganizationSerializer, RegionSerializer

logger = logging.getLogger(__name__)

@extend_schema_view(
    list=extend_schema(summary="List Organizations"),
    retrieve=extend_schema(summary="Get Organization"),
    create=extend_schema(summary="Create Organization"),
    update=extend_schema(summary="Update Organization"),
    partial_update=extend_schema(summary="Partial Update Organization"),
    destroy=extend_schema(summary="Delete Organization")
)
class OrganizationViewSet(BaseViewSet):
    """API endpoints for managing Organizations."""
    action_permission_mapping: ClassVar[dict[str, str]] = {
        'brands': AppPermissions.READ_ORGANIZATION,
        'active': AppPermissions.READ_ORGANIZATION,
        'toggle_status': AppPermissions.MANAGE_ORGANIZATION,
    }

    organization_field = 'id'
    permission_mapping: ClassVar[dict[str, str]] = {
        'GET': AppPermissions.READ_ORGANIZATION,
        'POST': AppPermissions.MANAGE_ORGANIZATION,
        'PUT': AppPermissions.MANAGE_ORGANIZATION,
        'PATCH': AppPermissions.MANAGE_ORGANIZATION,
        'DELETE': AppPermissions.MANAGE_ORGANIZATION
    }
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    search_fields = ('name', 'description')
    ordering_fields = ('name', 'status', 'created_at', 'updated_at')

    def perform_create(self, serializer):
        """Perform create."""
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        """Perform update."""
        serializer.save(updated_by=self.request.user)

    @extend_schema(summary="Get Organization Brands", responses={200: BrandSerializer(many=True)})
    @action(detail=True, methods=['get'], url_path='brands')
    def organization_brands(self, request, pk=None, id=None, **kwargs):
        """Retrieve a paginated list of active brands belonging to this organization."""
        logger.info(f"Fetching brands for organization pk {pk or id}")
        organization = self.get_object()
        brands = organization.brand_set.alive()
        page = self.paginate_queryset(brands)
        if page is not None:
            serializer = BrandSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = BrandSerializer(brands, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(summary="List Brands"),
    retrieve=extend_schema(summary="Get Brand"),
    create=extend_schema(summary="Create Brand"),
    update=extend_schema(summary="Update Brand"),
    partial_update=extend_schema(summary="Partial Update Brand"),
    destroy=extend_schema(summary="Delete Brand")
)
class BrandViewSet(BaseViewSet):
    """API endpoints for managing Brands."""
    action_permission_mapping: ClassVar[dict[str, str]] = {
        'toggle_status': AppPermissions.MANAGE_BRAND,
        'list_active': AppPermissions.READ_BRAND,
    }
    organization_field = 'organization_id'
    permission_mapping: ClassVar[dict[str, str]] = {
        'GET': AppPermissions.READ_BRAND,
        'POST': AppPermissions.MANAGE_BRAND,
        'PUT': AppPermissions.MANAGE_BRAND,
        'PATCH': AppPermissions.MANAGE_BRAND,
        'DELETE': AppPermissions.MANAGE_BRAND
    }
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    search_fields = ("name", "description")
    ordering_fields = ("name", "created_at", "updated_at")

    def get_queryset(self):
        """Get queryset."""
        queryset = super().get_queryset()
        org_id = self.request.query_params.get('organization')
        if org_id:
            queryset = queryset.filter(organization_id=org_id)
        return queryset

    def perform_create(self, serializer):
        """Perform create."""
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        """Perform update."""
        serializer.save(updated_by=self.request.user)

    @extend_schema(summary="Toggle Brand Status", request=dict, responses={200: dict})
    @action(detail=True, methods=["post"], url_path="toggle-status")
    def toggle_status(self, request, pk=None):
        """Toggle the active status of a brand (enable/disable)."""
        logger.info(f"Toggling status for brand pk {pk}")
        brand = self.get_object()
        is_active = request.data.get("is_active")

        if is_active is None:
            logger.warning(f"toggle_status called without 'is_active' for brand pk {pk}")
            return Response(
                {"detail": "Please provide 'is_active' in request body (true/false)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        brand.is_active = bool(is_active)
        brand.save()
        msg = "Brand activated successfully" if brand.is_active else "Brand deactivated successfully"
        logger.info(f"Brand pk {pk} status set to {brand.is_active}")
        return Response({"detail": msg}, status=status.HTTP_200_OK)

    @extend_schema(summary="List Active Brands", responses={200: BrandSerializer(many=True)})
    @action(detail=False, methods=["get"], url_path="active")
    def list_active(self, request):
        """Retrieve a list of only active (enabled) brands."""
        logger.info("Fetching active brands")
        active_brands = self.get_queryset().filter(is_active=True)
        page = self.paginate_queryset(active_brands)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(active_brands, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(summary="List Competitors"),
    retrieve=extend_schema(summary="Get Competitor"),
    create=extend_schema(summary="Create Competitor"),
    update=extend_schema(summary="Update Competitor"),
    partial_update=extend_schema(summary="Partial Update Competitor"),
    destroy=extend_schema(summary="Delete Competitor")
)
class CompetitorViewSet(BaseViewSet):
    """API endpoints for managing market Competitors."""
    organization_field = 'organization_id'
    permission_mapping: ClassVar[dict[str, str]] = {
        'GET': AppPermissions.READ_BRAND,
        'POST': AppPermissions.MANAGE_BRAND,
        'PUT': AppPermissions.MANAGE_BRAND,
        'PATCH': AppPermissions.MANAGE_BRAND,
        'DELETE': AppPermissions.MANAGE_BRAND
    }
    queryset = Competitor.objects.all()
    serializer_class = CompetitorSerializer
    search_fields = ("name", "description")
    ordering_fields = ("name", "created_at", "updated_at")

    def get_queryset(self):
        """Get queryset."""
        queryset = super().get_queryset()
        brand_id = self.request.query_params.get('brand')
        if brand_id:
            queryset = queryset.filter(region__brand_id=brand_id)

        region_id = self.request.query_params.get('region')
        if region_id:
            queryset = queryset.filter(region_id=region_id)

        return queryset

@extend_schema_view(
    list=extend_schema(summary="List Regions"),
    retrieve=extend_schema(summary="Get Region"),
    create=extend_schema(summary="Create Region"),
    update=extend_schema(summary="Update Region"),
    partial_update=extend_schema(summary="Partial Update Region"),
    destroy=extend_schema(summary="Delete Region")
)
class RegionViewSet(BaseViewSet):
    """API endpoints for managing operational Regions."""
    permission_mapping: ClassVar[dict[str, str]] = {
        'GET': AppPermissions.READ_BRAND,
        'POST': AppPermissions.MANAGE_BRAND,
        'PUT': AppPermissions.MANAGE_BRAND,
        'PATCH': AppPermissions.MANAGE_BRAND,
        'DELETE': AppPermissions.MANAGE_BRAND
    }
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    search_fields = ("name", "code")
    ordering_fields = ("name", "created_at", "updated_at")

    def get_queryset(self):
        """Get queryset."""
        queryset = super().get_queryset()
        brand_id = self.request.query_params.get('brand')
        if brand_id:
            if ',' in brand_id:
                queryset = queryset.filter(brand_id__in=brand_id.split(','))
            else:
                queryset = queryset.filter(brand_id=brand_id)
        return queryset

    @extend_schema(summary="Get Platforms for Region", responses={200: dict})
    @action(detail=True, methods=['get'], url_path='platforms')
    def region_platforms(self, request, pk=None, id=None, **kwargs):
        """Retrieve platforms used by active locations or keywords in this region."""
        region = self.get_object()
        from experience_cloud.catalog.models import Keyword, Location, Platform

        # Get distinct platform IDs used by active locations and keywords for this region
        loc_platforms = set(
            Location.objects.filter(region=region, is_active=True).values_list('platform_id', flat=True)
        )
        kw_platforms = set(Keyword.objects.filter(region=region, is_active=True).values_list('platform_id', flat=True))

        platform_ids = loc_platforms.union(kw_platforms)

        platforms = Platform.objects.filter(id__in=platform_ids, status='Active')

        # We use PlatformSerializer if available, otherwise just basic dict
        data = platforms.values('id', 'name', 'code')
        return Response(list(data), status=status.HTTP_200_OK)

