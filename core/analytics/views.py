import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from core.users.models import User
from core.organizations.models import Brand, Organization
from experience_cloud.executions.models import ActiveExecution

logger = logging.getLogger(__name__)

class DashboardDataView(APIView):
    """Global system metrics dashboard."""

    @extend_schema(summary="Get System Global Metrics", tags=["Global Analytics"])
    def get(self, request):
        logger.info("Fetching global system metrics")
        users_count = User.objects.count()
        brands_count = Brand.objects.count()
        orgs_count = Organization.objects.count()
        
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
            "recent_executions": executions_data
        }, status=200)
