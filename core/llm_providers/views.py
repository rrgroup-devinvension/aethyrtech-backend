import logging
from typing import ClassVar

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.authentication.permissions import AppPermissions
from shared.base.views import BaseViewSet
from shared.pagination import EnterpriseOffsetPagination

from .models import LLMProvider, TokenUsageLog
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
    """API endpoints for managing LLM Providers.

    Provides standard CRUD operations as well as custom actions to toggle
    status, set defaults, and test API connections securely.
    """
    organization_field = None
    action_permission_mapping: ClassVar[dict[str, str]] = {
        'set_status': AppPermissions.UPDATE_LLM_PROVIDER,
        'set_default': AppPermissions.UPDATE_LLM_PROVIDER,
        'test_connection': AppPermissions.READ_LLM_PROVIDERS,
    }
    permission_mapping: ClassVar[dict[str, str]] = {
        'GET': AppPermissions.READ_LLM_PROVIDERS,
        'POST': AppPermissions.CREATE_LLM_PROVIDER,
        'PUT': AppPermissions.UPDATE_LLM_PROVIDER,
        'PATCH': AppPermissions.UPDATE_LLM_PROVIDER,
        'DELETE': AppPermissions.DELETE_LLM_PROVIDER
    }
    queryset = LLMProvider.objects.all().order_by('id')
    serializer_class = LLMProviderSerializer
    search_fields = ('name', 'model')
    ordering_fields = ('id', 'name', 'model', 'created_at', 'updated_at', 'enabled')
    filterset_fields: ClassVar[tuple] = ('enabled',)

    def perform_update(self, serializer):
        instance = self.get_object()
        changed = False
        if 'model' in serializer.validated_data and serializer.validated_data['model'] != instance.model:
            changed = True
        if 'base_url' in serializer.validated_data and serializer.validated_data['base_url'] != instance.base_url:
            changed = True
        if 'api_key' in serializer.validated_data and serializer.validated_data['api_key'] != instance.api_key:
            changed = True

        if changed:
            serializer.validated_data['health_check_status'] = 'NOT TESTED'
            serializer.validated_data['last_health_check'] = None

        super().perform_update(serializer)

    @extend_schema(summary="Set LLM Provider Status", request=dict, responses={200: dict})
    @action(detail=True, methods=["post"], url_path="set-status")
    def set_status(self, request, id=None):
        """Enable or disable a specific LLM Provider.

        Requires a boolean 'enabled' in the request payload.
        """
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

    @extend_schema(summary="Set LLM Provider as Default", request=dict, responses={200: dict})
    @action(detail=True, methods=["post"], url_path="set-default")
    def set_default(self, request, id=None):
        """Mark a specific LLM Provider as the system-wide default.

        The model's save method automatically un-sets any previous default.
        """
        logger.info(f"Setting default for LLM Provider id {id}")
        provider = self.get_object()
        is_default = request.data.get("is_default")
        if is_default is None:
            return Response(
                {"detail": "Please provide 'is_default': true/false in request body."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        provider.is_default = bool(is_default)
        provider.save()
        msg = "Provider set as default" if provider.is_default else "Provider removed from default"
        return Response({"detail": msg}, status=status.HTTP_200_OK)

    @extend_schema(summary="Test LLM Provider Connection", request=None, responses={200: dict})
    @action(detail=True, methods=["post"], url_path="test-connection")
    def test_connection(self, request, id=None):
        """Test the API connection for an existing provider.

        Initializes the respective LLMService and pings the endpoint. Updates the
        health check status in the database based on the result.
        """
        logger.info(f"Testing connection for LLM Provider id {id}")
        provider = self.get_object()

        from core.llm_providers.services.llm_service import LLMService
        try:
            service = LLMService.get_service(provider=provider)
            response_body = service.test_connection()
            provider.health_check_status = 'UP'
        except (ValueError, ConnectionError, TimeoutError, RuntimeError) as e:
            provider.health_check_status = 'DOWN (Exception)'
            response_body = str(e)
            logger.error(f"Test connection failed: {e}")

        provider.last_health_check = timezone.now()
        provider.save()

        return Response({
            "health_check_status": provider.health_check_status,
            "last_health_check": provider.last_health_check,
            "response_body": response_body
        }, status=status.HTTP_200_OK)

    @extend_schema(summary="Test New LLM Provider Connection", request=dict, responses={200: dict})
    @action(detail=False, methods=["post"], url_path="test-connection")
    def test_new_connection(self, request):
        """Test an API connection dynamically without saving the provider.

        Useful for validating credentials on the frontend before committing
        a new provider to the database.
        """
        logger.info("Testing new connection for LLM Provider")

        api_key = request.data.get('api_key')
        name = request.data.get('name')
        model = request.data.get('model')

        if not api_key:
            return Response({"detail": "API Key is required to test connection"}, status=status.HTTP_400_BAD_REQUEST)
        if not name:
            return Response(
                {"error": "Failed to import required service class to test connection (e.g. Gemini, OpenAI)"},
                status=status.HTTP_400_BAD_REQUEST
            )

        from core.llm_providers.models import LLMProvider
        from core.llm_providers.services.llm_service import LLMService

        # Determine if api_key is encrypted already. If so, decrypt it for the mock test.
        # This occurs when testing from the detail page before saving changes.
        from experience_cloud.api_provider.utils import decrypt_string
        if api_key.startswith(('gAAAAAB', 'b64:')):
            api_key = decrypt_string(api_key)

        # Create a mock provider for testing
        mock_provider = LLMProvider(name=name, api_key=api_key, model=model)

        try:
            service = LLMService.get_service(provider=mock_provider)
            response_body = service.test_connection()
            health_check_status = 'UP'
        except (ValueError, ConnectionError, TimeoutError, RuntimeError) as e:
            health_check_status = 'DOWN (Exception)'
            response_body = str(e)
            logger.error(f"Test new connection failed: {e}")

        return Response({
            "health_check_status": health_check_status,
            "response_body": response_body
        }, status=status.HTTP_200_OK)
class LLMAnalysisViewSet(viewsets.ViewSet):
    """API endpoints for visualizing LLM Token usage and metrics.

    Delivers aggregated KPIs and charts for admin dashboards.
    """
    from shared.serializers import EmptySerializer
    serializer_class = EmptySerializer
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Retrieve a high-level summary of token consumption.

        Returns total KPIs, a daily burn rate time series, and a distribution
        doughnut chart broken down by Brand.
        """
        # 1. Total KPIs
        total_stats = TokenUsageLog.objects.aggregate(
            total_requests=Count('id'),
            total_prompt_tokens=Sum('prompt_tokens', default=0),
            total_completion_tokens=Sum('completion_tokens', default=0),
            total_cost=Sum('estimated_cost', default=0.00)
        )

        # 2. Daily Token Burn (Bar Chart)
        daily_stats = TokenUsageLog.objects.annotate(
            date=TruncDate('timestamp')
        ).values('date').annotate(
            total_tokens=Sum('total_tokens', default=0)
        ).order_by('date')

        time_labels = [str(ds['date']) for ds in daily_stats if ds['date']]
        time_data = [ds['total_tokens'] for ds in daily_stats if ds['date']]

        # 3. Brand Distribution (Doughnut Chart)
        brand_stats = TokenUsageLog.objects.values('brand_name').annotate(
            total_tokens=Sum('total_tokens', default=0)
        ).order_by('-total_tokens')

        brand_labels = [bs['brand_name'] or 'Unknown' for bs in brand_stats]
        brand_data = [bs['total_tokens'] for bs in brand_stats]



        return Response({
            "status": "ok",
            "kpis": {
                "total_requests": total_stats['total_requests'],
                "total_prompt_tokens": total_stats['total_prompt_tokens'],
                "total_completion_tokens": total_stats['total_completion_tokens'],
                "total_cost": float(total_stats['total_cost'])
            },
            "charts": {
                "time_series": {
                    "labels": time_labels,
                    "datasets": [
                        {
                            "label": "Total Tokens Consumed",
                            "data": time_data,
                            "backgroundColor": "#10b981",
                            "borderRadius": 6,
                            "barPercentage": 0.6
                        }
                    ]
                },
                "brand_distribution": {
                    "labels": brand_labels,
                    "datasets": [
                        {
                            "data": brand_data,
                            "backgroundColor": ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ef4444"],
                            "borderWidth": 0,
                            "hoverOffset": 4
                        }
                    ]
                }
            }
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def history(self, request):
        """Retrieve paginated token usage logs for auditing."""
        queryset = TokenUsageLog.objects.select_related('provider').order_by('-timestamp')
        paginator = EnterpriseOffsetPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)

        history_data = [
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "brand": log.brand_name or "Unknown",
                "type": log.type or "Unknown",
                "total_tokens": log.total_tokens,
                "prompt_tokens": log.prompt_tokens,
                "completion_tokens": log.completion_tokens,
                "estimated_cost": float(log.estimated_cost)
            }
            for log in (page if page is not None else queryset)
        ]

        if page is not None:
            return paginator.get_paginated_response(history_data)

        return Response(history_data, status=status.HTTP_200_OK)
