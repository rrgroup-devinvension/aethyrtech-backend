from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
import logging
import requests
from django.utils import timezone
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

    @extend_schema(summary="Set LLM Provider Status", request=dict, responses={200: dict})
    @action(detail=True, methods=["post"], url_path="set-status")
    def set_status(self, request, id=None):
        logger.info(f"Setting status for LLM Provider id {id}")
        provider = self.get_object()
        enabled = request.data.get("enabled")
        if enabled is None:
            return Response(
                {"detail": "Please provide 'enabled': true/false in request body."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        provider.enabled = bool(enabled)
        provider.save()
        msg = "Provider enabled successfully" if provider.enabled else "Provider disabled successfully"
        return Response({"detail": msg}, status=status.HTTP_200_OK)

    @extend_schema(summary="Test LLM Provider Connection", request=None, responses={200: dict})
    @action(detail=True, methods=["post"], url_path="test-connection")
    def test_connection(self, request, id=None):
        logger.info(f"Testing connection for LLM Provider id {id}")
        provider = self.get_object()
        
        if not provider.base_url:
            return Response({"detail": "Base URL is required to test connection"}, status=status.HTTP_400_BAD_REQUEST)
            
        test_url = provider.base_url.rstrip('/')
        if provider.health_check_path:
            test_url = f"{test_url}/{provider.health_check_path.lstrip('/')}"
            
        headers = {}
        if provider.api_key:
            headers['Authorization'] = f"Bearer {provider.api_key}"
            
        try:
            res = requests.get(test_url, headers=headers, timeout=provider.timeout_seconds or 10)
            if res.status_code < 400:
                provider.health_check_status = 'UP'
            else:
                provider.health_check_status = f'DOWN ({res.status_code})'
        except Exception as e:
            provider.health_check_status = 'DOWN (Exception)'
            
        provider.last_health_check = timezone.now()
        provider.save()
        
        return Response({
            "health_check_status": provider.health_check_status,
            "last_health_check": provider.last_health_check
        }, status=status.HTTP_200_OK)
