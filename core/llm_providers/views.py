import logging
from drf_spectacular.utils import extend_schema, extend_schema_view
from shared.base.views import BaseViewSet
from .models import LLMProvider
from .serializers import LLMProviderSerializer

logger = logging.getLogger(__name__)

@extend_schema_view(
    list=extend_schema(summary="List LLM Providers"),
    retrieve=extend_schema(summary="Get LLM Provider"),
    create=extend_schema(summary="Create LLM Provider"),
    update=extend_schema(summary="Update LLM Provider"),
    partial_update=extend_schema(summary="Partial Update LLM Provider"),
    destroy=extend_schema(summary="Delete LLM Provider")
)
class LLMProviderViewSet(BaseViewSet):
    queryset = LLMProvider.objects.all().order_by('name')
    serializer_class = LLMProviderSerializer
    search_fields = ('name', 'model')
    ordering_fields = ('name', 'created_at', 'updated_at', 'enabled')
