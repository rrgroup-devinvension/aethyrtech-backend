import logging
from typing import ClassVar

from drf_spectacular.utils import extend_schema, extend_schema_view

from core.authentication.permissions import AppPermissions
from shared.base.views import BaseViewSet

from .models import Category
from .serializers import CategoryDetailSerializer, CategorySerializer

logger = logging.getLogger(__name__)

@extend_schema_view(
    list=extend_schema(summary="List Categories"),
    retrieve=extend_schema(summary="Get Category"),
    create=extend_schema(summary="Create Category"),
    update=extend_schema(summary="Update Category"),
    partial_update=extend_schema(summary="Partial Update Category"),
    destroy=extend_schema(summary="Delete Category")
)
class CategoryViewSet(BaseViewSet):
    """ViewSet for managing categories.

    Provides standard CRUD operations for the Category model and custom routing
    for managing related entities like pincodes and keywords.
    """
    action_permission_mapping: ClassVar[dict[str, str]] = {
        'pincodes': AppPermissions.READ_CATEGORIES,
        'pincodes/add': AppPermissions.UPDATE_CATEGORY,
        'pincodes/update/(?P<pincode_id>[^/.]+)': AppPermissions.UPDATE_CATEGORY,
        'pincodes/remove/(?P<pincode_id>[^/.]+)': AppPermissions.UPDATE_CATEGORY,
        'pincodes/clear': AppPermissions.UPDATE_CATEGORY,
        'pincodes/upload-csv': AppPermissions.UPDATE_CATEGORY,
        'keywords': AppPermissions.READ_CATEGORIES,
        'keywords/add': AppPermissions.UPDATE_CATEGORY,
        'keywords/update/(?P<keyword_id>[^/.]+)': AppPermissions.UPDATE_CATEGORY,
        'keywords/remove/(?P<keyword_id>[^/.]+)': AppPermissions.UPDATE_CATEGORY,
        'keywords/remove-by-platform': AppPermissions.UPDATE_CATEGORY,
        'keywords/clear': AppPermissions.UPDATE_CATEGORY,
        'keywords/upload-csv': AppPermissions.UPDATE_CATEGORY,
    }

    organization_field = None
    permission_mapping: ClassVar[dict[str, str]] = {
        'GET': AppPermissions.READ_CATEGORIES,
        'POST': AppPermissions.CREATE_CATEGORY,
        'PUT': AppPermissions.UPDATE_CATEGORY,
        'PATCH': AppPermissions.UPDATE_CATEGORY,
        'DELETE': AppPermissions.DELETE_CATEGORY
    }
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    search_fields = ('name', 'description')
    filterset_fields = ('status',)
    ordering_fields = ('id', 'name', 'created_at', 'updated_at')
    ordering = ('id',)

    def get_serializer_class(self):
        """Dynamically determine the serializer class based on the action.

        Uses CategoryDetailSerializer for retrieving a single category,
        and CategorySerializer for listing and writing.
        """
        if self.action == 'retrieve':
            return CategoryDetailSerializer
        return CategorySerializer

    def perform_create(self, serializer):
        """Save the new category."""
        logger.info("Creating a new category")
        serializer.save()

    def perform_update(self, serializer):
        """Save the updated category."""
        logger.info(f"Updating category {self.get_object().id}")
        serializer.save()

