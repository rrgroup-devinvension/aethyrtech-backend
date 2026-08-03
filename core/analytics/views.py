import logging

from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.llm_providers.models import LLMProvider
from core.organizations.models import Brand, Organization, Region
from core.users.models import User
from experience_cloud.api_provider.models import ApiProvider
from experience_cloud.executions.models import ActiveExecution

logger = logging.getLogger(__name__)

class DashboardDataView(APIView):
    """Global system metrics dashboard."""

    @extend_schema(summary="Get System Global Metrics", tags=["Global Analytics"])
    def get(self, request):
        """Retrieve global system metrics for the dashboard.

        This endpoint aggregates top-level counts for core entities including
        users, brands, and organizations. It also fetches a list of the 20
        most recent active executions across the system to display current
        processing activity.

        Returns:
            Response: A JSON payload containing the aggregate counts and recent execution data.
        """
        logger.info("Fetching global system metrics")
        users_count = User.objects.count()
        brands_count = Brand.objects.count()
        orgs_count = Organization.objects.count()
        regions_count = Region.objects.count()
        api_providers_count = ApiProvider.objects.count()
        llm_providers_count = LLMProvider.objects.count()

        # Execution stats
        exec_running = ActiveExecution.objects.filter(status='RUNNING').count()
        exec_pending = ActiveExecution.objects.filter(status='PENDING').count()
        exec_failed = ActiveExecution.objects.filter(status='FAILED').count()

        # Recent running executions as a stand-in for "scraping logs"
        recent_executions = ActiveExecution.objects.order_by('-started_at')[:20]

        executions_data = [
            {
                "id": str(exec.id),
                "type": exec.execution_type,
                "status": exec.status,
                "started_at": exec.started_at
            } for exec in recent_executions
        ]

        return Response({
            "users_count": users_count,
            "brands_count": brands_count,
            "organizations_count": orgs_count,
            "regions_count": regions_count,
            "providers_count": api_providers_count + llm_providers_count,
            "execution_stats": {
                "running": exec_running,
                "pending": exec_pending,
                "failed": exec_failed
            },
            "recent_executions": executions_data
        }, status=200)
