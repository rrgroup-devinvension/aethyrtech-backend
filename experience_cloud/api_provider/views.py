import logging
from typing import ClassVar, Literal, cast

from django.db.models import Avg, Count, Sum
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.authentication.permissions import AppPermissions
from shared.base.views import BaseViewSet
from shared.pagination import EnterpriseOffsetPagination

from .exceptions import ApiProviderConfigurationError, ApiProviderRequestError
from .models import ApiProvider, APIUsageLog, APIUsageSummary
from .serializers import ApiProviderSerializer
from .services import BaseApiClient

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
    """CRUD operations for managing API Providers and executing health checks."""
    action_permission_mapping: ClassVar[dict] = {
        'set_status': AppPermissions.UPDATE_API_PROVIDER,
        'test_connection': AppPermissions.READ_API_PROVIDERS,
        'test_new_connection': AppPermissions.READ_API_PROVIDERS,
    }

    permission_mapping: ClassVar[dict] = {
        'GET': AppPermissions.READ_API_PROVIDERS,
        'POST': AppPermissions.CREATE_API_PROVIDER,
        'PUT': AppPermissions.UPDATE_API_PROVIDER,
        'PATCH': AppPermissions.UPDATE_API_PROVIDER,
        'DELETE': AppPermissions.DELETE_API_PROVIDER
    }

    queryset = ApiProvider.objects.all().order_by('id')
    serializer_class = ApiProviderSerializer
    search_fields = ('name', 'code')
    ordering_fields = ('id', 'name', 'code', 'auth_type', 'health_check_status', 'status')
    filterset_fields: ClassVar[tuple] = ('auth_type', 'health_check_status', 'status')

    @action(detail=False, methods=['get'], url_path='form-options')
    def form_options(self, request, *args, **kwargs):
        """Return all valid enums for the frontend form in a single request."""
        from .models import ApiProviderCodes

        return Response({
            "providerCodes": [{"id": k, "name": v} for k, v in ApiProviderCodes.choices],
        })

    @extend_schema(summary="Set API Provider Status", request=dict, responses={200: dict})
    @action(detail=True, methods=["post"], url_path="set-status")
    def set_status(self, request, id=None):
        """Set status of API Provider."""
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
        """Test connection for API Provider."""
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


        method_str = getattr(provider, 'test_http_method', 'GET').upper()
        method = cast(Literal["GET", "POST", "PUT", "PATCH", "DELETE"], method_str)
        payload = getattr(provider, 'test_payload', {})

        # Simple test connection
        try:
            client = BaseApiClient(provider=provider)
            response_body = client.request(
                method=method,
                endpoint=provider.health_check_path or '',
                json=payload if method in ['POST', 'PUT', 'PATCH'] else None
            )
            provider.health_check_status = 'UP'
        except (ApiProviderConfigurationError, ApiProviderRequestError) as e:
            if isinstance(e, ApiProviderRequestError) and e.extra:
                status_code = e.extra.get('status_code')
                provider.health_check_status = f'DOWN ({status_code})' if status_code else 'DOWN (Exception)'
                response_body = e.extra.get('body') or str(e)
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
        """Test new connection for API Provider."""
        logger.info("Testing new connection for API Provider")
        base_url = request.data.get('base_url')
        health_check_path = request.data.get('health_check_path')
        timeout = request.data.get('timeout', 10)

        if not base_url:
            return Response({"detail": "Base URL is not configured"}, status=status.HTTP_400_BAD_REQUEST)

        headers = request.data.get('default_headers', {})
        try:
            if isinstance(headers, str):
                import json
                headers = json.loads(headers)
        except (ValueError, TypeError):
            headers = {}

        method_str = request.data.get('test_http_method', 'GET').upper()
        method = cast(Literal["GET", "POST", "PUT", "PATCH", "DELETE"], method_str)
        payload = request.data.get('test_payload', {})
        try:
            if isinstance(payload, str):
                import json
                payload = json.loads(payload)
        except (ValueError, TypeError):
            payload = {}

        credentials = request.data.get('credentials', {})
        try:
            if isinstance(credentials, str):
                import json
                credentials = json.loads(credentials)
        except (ValueError, TypeError):
            credentials = {}

        provider_id = request.data.get('id')

        provider = ApiProvider(
            id=provider_id,
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
        except (ApiProviderConfigurationError, ApiProviderRequestError) as e:
            logger.error(f"Test new connection failed: {e}")
            if isinstance(e, ApiProviderRequestError) and e.extra:
                status_code = e.extra.get('status_code')
                health_check_status = f'DOWN ({status_code})' if status_code else 'DOWN (Exception)'
                response_body = e.extra.get('body') or str(e)
            else:
                health_check_status = 'DOWN (Exception)'
                response_body = str(e)

        if provider_id:
            try:
                db_provider = ApiProvider.objects.get(id=provider_id)
                db_provider.health_check_status = health_check_status
                db_provider.last_health_check = timezone.now()
                db_provider.save(update_fields=['health_check_status', 'last_health_check'])
            except ApiProvider.DoesNotExist as e:
                logger.error(f"Failed to update provider status: {e}")

        return Response({
            "detail": f"Health check completed: {health_check_status}",
            "health_check_status": health_check_status,
            "response_body": response_body,
            "last_health_check": timezone.now()
        }, status=status.HTTP_200_OK)

class ApiProviderAnalysisViewSet(viewsets.ViewSet):
    """API ViewSet for generating analytical charts and usage history for all configured API Providers."""
    from shared.serializers import EmptySerializer
    serializer_class = EmptySerializer

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Retrieve aggregated KPI summaries and charting data for API usages."""
        # KPIs from Summaries
        summaries = APIUsageSummary.objects.all()
        agg = summaries.aggregate(
            total_calls=Sum('total_calls'),
            success_calls=Sum('success_calls'),
            failed_calls=Sum('failed_calls'),
            total_cost=Sum('total_cost')
        )

        total_calls = agg['total_calls'] or 0
        success_calls = agg['success_calls'] or 0
        total_cost = agg['total_cost'] or 0.0
        success_rate = (success_calls / total_calls * 100) if total_calls > 0 else 0

        # Avg response time from logs
        logs = APIUsageLog.objects.all()
        avg_rt = logs.aggregate(avg_time=Avg('response_time'))['avg_time'] or 0

        # Time Series Chart
        # Group by date from summaries
        daily_stats = summaries.values('date').annotate(
            calls=Sum('total_calls')
        ).order_by('date')

        time_series = {
            "labels": [s['date'].strftime('%b %d') for s in daily_stats],
            "datasets": [{
                "label": "Total Calls",
                "data": [s['calls'] for s in daily_stats],
                "backgroundColor": "#3b82f6",
                "borderRadius": 4,
            }]
        }

        # Status Distribution Chart from Logs
        status_dist = logs.values('status').annotate(count=Count('id'))
        status_labels = []
        status_data = []
        status_colors = []
        for s in status_dist:
            status_labels.append(s['status'])
            status_data.append(s['count'])
            if s['status'] == 'SUCCESS':
                status_colors.append('#10b981')
            elif s['status'] == 'FAILED':
                status_colors.append('#ef4444')
            else:
                status_colors.append('#f59e0b')

        status_distribution = {
            "labels": status_labels,
            "datasets": [{
                "data": status_data,
                "backgroundColor": status_colors,
                "borderWidth": 0
            }]
        }

        return Response({
            "status": "ok",
            "data": {
                "kpis": {
                    "total_calls": total_calls,
                    "success_rate": round(success_rate, 2),
                    "avg_response_time": round(avg_rt, 2),
                    "total_cost": float(total_cost)
                },
                "charts": {
                    "time_series": time_series,
                    "status_distribution": status_distribution
                }
            }
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def history(self, request):
        """Retrieve a paginated list of all API usage request logs."""
        queryset = APIUsageLog.objects.select_related('api_provider').order_by('-timestamp')
        paginator = EnterpriseOffsetPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)

        data = []
        for log in (page if page is not None else queryset):
            data.append({
                "id": log.id,
                "timestamp": log.timestamp,
                "provider_name": log.api_provider.name if log.api_provider else "Unknown",
                "status": log.status,
                "response_time": log.response_time,
                "cost": log.cost,
            })

        if page is not None:
            return paginator.get_paginated_response(data)

        return Response({
            "status": "ok",
            "count": len(data),
            "results": data
        })
