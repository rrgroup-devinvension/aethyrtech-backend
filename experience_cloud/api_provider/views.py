import requests
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
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

    @extend_schema(summary="Set API Provider Status", request=dict, responses={200: dict})
    @action(detail=True, methods=["post"], url_path="set-status")
    def set_status(self, request, id=None):
        logger.info(f"Setting status for API Provider id {id}")
        provider = self.get_object()
        status_val = request.data.get("status")
        if status_val is None:
            return Response(
                {"detail": "Please provide 'status' in request body (e.g. 'ACTIVE', 'INACTIVE')."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        provider.status = status_val
        provider.save()
        msg = f"Provider status updated to {status_val} successfully"
        return Response({"detail": msg}, status=status.HTTP_200_OK)

    @extend_schema(summary="Test API Provider Connection", request=None, responses={200: dict})
    @action(detail=True, methods=["post"], url_path="test-connection")
    def test_connection(self, request, id=None):
        logger.info(f"Testing connection for API Provider id {id}")
        provider = self.get_object()
        
        if not provider.base_url:
            return Response({"detail": "Base URL is not configured"}, status=status.HTTP_400_BAD_REQUEST)
            
        test_url = provider.base_url.rstrip('/')
        if provider.health_check_path:
            # ensure health_check_path starts with /
            if not provider.health_check_path.startswith('/'):
                test_url += '/' + provider.health_check_path
            else:
                test_url += provider.health_check_path
                
        headers = provider.default_headers or {}
        
        # Simple test connection
        try:
            res = requests.get(test_url, headers=headers, timeout=provider.timeout or 10)
            if res.status_code < 400:
                provider.health_check_status = 'UP'
            else:
                provider.health_check_status = f'DOWN ({res.status_code})'
        except Exception as e:
            provider.health_check_status = 'DOWN (Exception)'
            
        provider.last_health_check = timezone.now()
        provider.save()
        
        return Response({
            "detail": f"Health check completed: {provider.health_check_status}",
            "health_check_status": provider.health_check_status,
            "last_health_check": provider.last_health_check
        }, status=status.HTTP_200_OK)
