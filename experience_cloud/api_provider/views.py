import logging
from drf_spectacular.utils import extend_schema, extend_schema_view
from shared.base.views import BaseViewSet
from .models import ApiProvider
from .serializers import ApiProviderSerializer

logger = logging.getLogger(__name__)

@extend_schema_view(
    list=extend_schema(summary="List API Providers"),
    retrieve=extend_schema(summary="Get API Provider"),
    create=extend_schema(summary="Create API Provider"),
    update=extend_schema(summary="Update API Provider"),
    partial_update=extend_schema(summary="Partial Update API Provider"),
    destroy=extend_schema(summary="Delete API Provider")
)
class ApiProviderViewSet(BaseViewSet):
    queryset = ApiProvider.objects.all().order_by('name')
    serializer_class = ApiProviderSerializer
    search_fields = ('name', 'base_url', 'status')
    ordering_fields = ('name', 'created_at', 'updated_at', 'status')
