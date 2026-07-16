import logging
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.response import Response
from shared.base.views import BaseViewSet
from .models import Category
from .serializers import CategorySerializer, CategoryDetailSerializer

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
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    search_fields = ('name', 'description')
    ordering_fields = ('name', 'created_at', 'updated_at')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CategoryDetailSerializer
        return CategorySerializer

    def perform_create(self, serializer):
        logger.info("Creating a new category")
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        logger.info(f"Updating category {self.get_object().id}")
        serializer.save(updated_by=self.request.user)

