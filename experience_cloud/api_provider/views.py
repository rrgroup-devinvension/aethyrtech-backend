from core.authentication.permissions import AppPermissions
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
    action_permission_mapping = {
        'set_status': AppPermissions.UPDATE_API_PROVIDER,
        'test_connection': AppPermissions.READ_API_PROVIDERS,
        'test_new_connection': AppPermissions.READ_API_PROVIDERS,
    }
    
    permission_mapping = {
        'GET': AppPermissions.READ_API_PROVIDERS,
        'POST': AppPermissions.CREATE_API_PROVIDER,
        'PUT': AppPermissions.UPDATE_API_PROVIDER,
        'PATCH': AppPermissions.UPDATE_API_PROVIDER,
        'DELETE': AppPermissions.DELETE_API_PROVIDER
    }

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
        method = getattr(provider, 'test_http_method', 'GET').upper()
        payload = getattr(provider, 'test_payload', {})
        
        from .services import BaseApiClient
        
        # Simple test connection
        try:
            client = BaseApiClient(provider=provider)
            response_body = client.request(
                method=method,
                endpoint=provider.health_check_path or '',
                json=payload if method in ['POST', 'PUT', 'PATCH'] else None
            )
            provider.health_check_status = 'UP'
        except Exception as e:
            if hasattr(e, 'response') and e.response is not None:
                provider.health_check_status = f'DOWN ({e.response.status_code})'
                try:
                    response_body = e.response.json()
                except:
                    response_body = e.response.text or str(e)
            else:
                provider.health_check_status = 'DOWN (Exception)'
                response_body = str(e)
            
        provider.last_health_check = timezone.now()
        provider.save()
        
        return Response({
            "detail": f"Health check completed: {provider.health_check_status}",
            "health_check_status": provider.health_check_status,
            "response_body": response_body,
            "last_health_check": provider.last_health_check
        }, status=status.HTTP_200_OK)

    @extend_schema(summary="Test New API Provider Connection", request=dict, responses={200: dict})
    @action(detail=False, methods=["post"], url_path="test-connection")
    def test_new_connection(self, request):
        logger.info(f"Testing new connection for API Provider")
        base_url = request.data.get('base_url')
        health_check_path = request.data.get('health_check_path')
        timeout = request.data.get('timeout', 10)
        
        if not base_url:
            return Response({"detail": "Base URL is not configured"}, status=status.HTTP_400_BAD_REQUEST)
        from .models import ApiProvider
        from .services import BaseApiClient
        
        headers = request.data.get('default_headers', {})
        try:
            if isinstance(headers, str):
                import json
                headers = json.loads(headers)
        except:
            headers = {}
            
        method = request.data.get('test_http_method', 'GET').upper()
        payload = request.data.get('test_payload', {})
        try:
            if isinstance(payload, str):
                import json
                payload = json.loads(payload)
        except:
            payload = {}
            
        credentials = request.data.get('credentials', {})
        try:
            if isinstance(credentials, str):
                import json
                credentials = json.loads(credentials)
        except:
            credentials = {}
            
        provider = ApiProvider(
            base_url=base_url,
            health_check_path=health_check_path or '',
            timeout=timeout,
            auth_type=request.data.get('auth_type', 'NONE'),
            credentials=credentials,
            default_headers=headers,
            status="ACTIVE"
        )
        
        try:
            client = BaseApiClient(provider=provider)
            response_body = client.request(
                method=method,
                endpoint=provider.health_check_path or '',
                json=payload if method in ['POST', 'PUT', 'PATCH'] else None
            )
            health_check_status = 'UP'
        except Exception as e:
            logger.error(f"Test new connection failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                health_check_status = f'DOWN ({e.response.status_code})'
                try:
                    response_body = e.response.json()
                except:
                    response_body = e.response.text or str(e)
            else:
                health_check_status = 'DOWN (Exception)'
                response_body = str(e)
            
        provider_id = request.data.get('id')
        if provider_id:
            try:
                db_provider = ApiProvider.objects.get(id=provider_id)
                db_provider.health_check_status = health_check_status
                db_provider.last_health_check = timezone.now()
                db_provider.save(update_fields=['health_check_status', 'last_health_check'])
            except Exception as e:
                logger.error(f"Failed to update provider status: {e}")
                
        return Response({
            "detail": f"Health check completed: {health_check_status}",
            "health_check_status": health_check_status,
            "response_body": response_body,
            "last_health_check": timezone.now()
        }, status=status.HTTP_200_OK)
