import logging
from datetime import datetime
from typing import ClassVar

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import APIException, NotFound
from rest_framework.response import Response

from core.authentication.permissions import AppPermissions
from experience_cloud.json_generator.models import TemplateCodes

from .views import RegionBaseDataView

logger = logging.getLogger(__name__)

class ActionPlansView(RegionBaseDataView):
    """API view for managing action plans and tasks.

    Supports fetching all plans, updating tasks, and sending email notifications.
    """
    permission_mapping: ClassVar[dict] = {
        'GET': AppPermissions.READ_ACTION_DASHBOARD,
        'PUT': AppPermissions.MANAGE_ACTION_PLANS
    }

    @extend_schema(summary="Get Action Plans", tags=["Action Dashboard"])
    def get(self, request, region_id: int, task_id: str | None = None):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            raise NotFound(detail="Region not found")

        try:
            plans_data = self.fetch_analytics_data(region, TemplateCodes.ACTION_PLANS)
        except NotFound:
            # If no plans exist yet, return empty structure
            plans_data = {"plans": {}, "last_modified": timezone.now().isoformat()}

        if task_id == "summary":
            summary = {
                "total": 0,
                "pending": 0,
                "assigned": 0,
                "in_progress": 0,
                "completed": 0,
                "verified": 0
            }
            plans_dict = plans_data.get("plans", {})
            if not isinstance(plans_dict, dict):
                plans_dict = {}
            for _plan_key, plan in plans_dict.items():
                for task in plan.get("tasks", []):
                    summary["total"] += 1
                    status = task.get("status", "pending")
                    if status in summary:
                        summary[status] += 1
                    else:
                        summary["pending"] += 1
            return Response({
                "success": True,
                "summary": summary
            })

        # Get team members from the DB
        from core.team_management.models import TeamMember
        from core.team_management.serializers import TeamMemberSerializer
        team_members = TeamMember.objects.filter(brand=region.brand)
        team_data = TeamMemberSerializer(team_members, many=True).data

        return Response({
            "success": True,
            "plans": plans_data.get("plans", {}),
            "team_members": team_data,
            "last_modified": plans_data.get("last_modified")
        })

    @extend_schema(summary="Update Action Plan Task", tags=["Action Dashboard"])
    def put(self, request, region_id: int, task_id: str):
        """Handle PUT request."""
        region = self.get_region_or_404(region_id)
        if not region:
            raise NotFound(detail="Region not found")

        insight_id = request.data.get("insight_id")
        if not insight_id:
            raise APIException("insight_id is required")

        try:
            plans_data = self.fetch_analytics_data(region, TemplateCodes.ACTION_PLANS)
        except NotFound as e:
            raise NotFound("Action plans not found") from e

        key = f"insight_{insight_id}"
        if key not in plans_data.get("plans", {}):
            raise NotFound(f"Plan not found for insight {insight_id}")

        updated_task = None

        # Find and update the target task
        for task in plans_data["plans"][key].get("tasks", []):
            if task.get("task_id") == task_id:
                if "status" in request.data:
                    task["status"] = request.data["status"]
                    if task["status"] in ["completed", "verified"]:
                        task["completed_at"] = timezone.now().isoformat()

                if "assigned_to" in request.data:
                    task["assigned_to"] = request.data["assigned_to"]
                    task["assigned_at"] = timezone.now().isoformat()
                    if task.get("status", "pending") == "pending" and request.data["assigned_to"]:
                        task["status"] = "assigned"

                if "notes" in request.data:
                    task["notes"] = request.data["notes"]
                if "due_date" in request.data:
                    task["due_date"] = request.data["due_date"]
                if "priority" in request.data:
                    task["priority"] = request.data["priority"]

                updated_task = task
                break

        if not updated_task:
            raise NotFound(f"Task {task_id} not found")

        # Linked task synchronization
        sync_count = 0
        linked_group = updated_task.get("linked_task_group")

        if linked_group:
            plans_dict = plans_data.get("plans", {})
            if isinstance(plans_dict, dict):
                for _p_key, plan in plans_dict.items():
                    for linked_task in plan.get("tasks", []):
                        if linked_task.get("task_id") == task_id:
                            continue
                        if linked_task.get("linked_task_group") != linked_group:
                            continue

                        changed = False
                    if "status" in request.data and linked_task.get("status") != request.data["status"]:
                        linked_task["status"] = request.data["status"]
                        if request.data["status"] in ["completed", "verified"]:
                            linked_task["completed_at"] = timezone.now().isoformat()
                        changed = True

                    if "assigned_to" in request.data:
                        linked_task["assigned_to"] = request.data["assigned_to"]
                        linked_task["assigned_at"] = timezone.now().isoformat()
                        if linked_task.get("status", "pending") == "pending" and request.data["assigned_to"]:
                            linked_task["status"] = "assigned"
                        changed = True

                    if changed:
                        sync_count += 1

        plans_data["last_modified"] = timezone.now().isoformat()
        self.save_analytics_data(region, TemplateCodes.ACTION_PLANS, plans_data)

        return Response({
            "success": True,
            "message": "Task updated",
            "linked_updates": sync_count
        })

class ActionPlansNotifyView(RegionBaseDataView):
    """API view for sending task assignment emails."""
    permission_mapping: ClassVar[dict] = {'POST': AppPermissions.MANAGE_ACTION_PLANS}
    @extend_schema(summary="Send Task Assignment Email", tags=["Action Dashboard"])
    def post(self, request, region_id: int):
        """Handle POST request."""
        region = self.get_region_or_404(region_id)
        if not region:
            raise NotFound(detail="Region not found")

        insight_id = request.data.get("insight_id")
        task_id = request.data.get("task_id")
        assigned_to = request.data.get("assigned_to")
        insight_title = request.data.get("insight_title", "Insight")

        if not all([insight_id, task_id, assigned_to]):
            raise APIException("insight_id, task_id, and assigned_to are required")

        # Fetch team member
        from core.team_management.models import TeamMember
        try:
            member = TeamMember.objects.get(id=assigned_to)
        except TeamMember.DoesNotExist:
            try:
                # Fallback to string matching if UUID wasn't used
                member = TeamMember.objects.filter(brand=region.brand, name=assigned_to).first()
                if not member:
                    raise NotFound("Team member not found")
            except Exception as e:
                raise NotFound("Team member not found") from e

        if not member.email:
            raise APIException("Team member does not have an email address configured")

        # Fetch task details
        try:
            plans_data = self.fetch_analytics_data(region, TemplateCodes.ACTION_PLANS)
        except NotFound as e:
            raise NotFound("Action plans not found") from e

        key = f"insight_{insight_id}"
        task = None
        for t in plans_data.get("plans", {}).get(key, {}).get("tasks", []):
            if t.get("task_id") == task_id:
                task = t
                break

        if not task:
            raise NotFound("Task not found")

        # Compose email
        brand_name = region.brand.name
        task_days = int(task.get("timeline_days", 14))

        import datetime
        due_date = (timezone.now() + datetime.timedelta(days=task_days)).strftime('%b %d, %Y')

        context = {
            "safe_brand": brand_name,
            "member_name": member.name,
            "safe_insight": insight_title,
            "task_title": task.get("title", "Untitled Task"),
            "task_desc": task.get("description", ""),
            "task_cat": task.get("category", ""),
            "task_pri": task.get("priority", "medium").capitalize(),
            "task_days": task_days,
            "due_date": due_date,
            "task_kpi": task.get("kpi", ""),
            "task_target": task.get("target_value", ""),
            "task_base": task.get("baseline_value", ""),
        }

        html_message = render_to_string('emails/task_assignment.html', context)
        plain_message = strip_tags(html_message)

        subject = f"[{brand_name}] Action Assigned: {context['task_title']}"

        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[member.email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            logger.error(f"Failed to send assignment email: {e!s}")
            raise APIException(f"Failed to send email: {e!s}") from e

        # Update last email sent info
        task["last_email_sent_at"] = timezone.now().isoformat()
        task["last_email_recipient"] = member.name

        plans_data["last_modified"] = timezone.now().isoformat()
        self.save_analytics_data(region, TemplateCodes.ACTION_PLANS, plans_data)

        return Response({
            "success": True,
            "message": f"Email sent to {member.email}"
        })


class MetricSnapshotsView(RegionBaseDataView):
    """API view for managing metric snapshots."""
    MAX_SNAPSHOTS = 5

    permission_mapping: ClassVar[dict] = {
        'GET': AppPermissions.READ_ACTION_DASHBOARD,
        'POST': AppPermissions.MANAGE_METRIC_SNAPSHOTS,
        'PUT': AppPermissions.MANAGE_METRIC_SNAPSHOTS,
        'DELETE': AppPermissions.MANAGE_METRIC_SNAPSHOTS
    }

    @extend_schema(summary="List Metric Snapshots", tags=["Action Dashboard"])
    def get(self, request, region_id: int):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            raise NotFound(detail="Region not found")

        try:
            snapshots_data = self.fetch_analytics_data(region, TemplateCodes.METRIC_SNAPSHOTS)
        except NotFound:
            snapshots_data = {"snapshots": []}

        return Response({
            "success": True,
            "snapshots": snapshots_data.get("snapshots", []),
            "count": len(snapshots_data.get("snapshots", []))
        })

    @extend_schema(summary="Capture Metric Snapshot", tags=["Action Dashboard"])
    def post(self, request, region_id: int):
        """Handle POST request."""
        region = self.get_region_or_404(region_id)
        if not region:
            raise NotFound(detail="Region not found")

        # We need to read current metrics. Normally this would read from `dashboard_data.json`
        try:
            dash_data = self.fetch_analytics_data(region, TemplateCodes.RISK_DATA)
        except NotFound as e:
            raise NotFound("Dashboard data not found to capture snapshot") from e

        # For simplicity, we just extract top level metrics from dash_data if they exist
        # Depending on structure, this could be customized
        metrics = {
            "health_score": dash_data.get("health_score"),
            "anxiety": dash_data.get("anxiety"),
            "share": dash_data.get("share"),
            "missing_descriptions": dash_data.get("missing_descriptions"),
            "missing_media": dash_data.get("missing_media"),
            "missing_reviews": dash_data.get("missing_reviews"),
            "oos_rate": dash_data.get("oos_rate"),
        }

        snapshot = {
            "snapshot_id": f"snap_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "captured_at": timezone.now().isoformat(),
            "trigger": request.data.get("trigger", "manual"),
            "metrics": {k: v for k, v in metrics.items() if v is not None}
        }

        try:
            snapshots_data = self.fetch_analytics_data(region, TemplateCodes.METRIC_SNAPSHOTS)
        except NotFound:
            snapshots_data = {"snapshots": []}

        snapshots_data["snapshots"].append(snapshot)

        # Trim to MAX_SNAPSHOTS
        if len(snapshots_data["snapshots"]) > self.MAX_SNAPSHOTS:
            snapshots_data["snapshots"] = snapshots_data["snapshots"][-self.MAX_SNAPSHOTS:]

        self.save_analytics_data(region, TemplateCodes.METRIC_SNAPSHOTS, snapshots_data)

        return Response({
            "success": True,
            "message": "Metric snapshot captured",
            "snapshot": snapshot
        })

class MetricSnapshotsCompareView(RegionBaseDataView):
    """API view for comparing two metric snapshots."""
    permission_mapping: ClassVar[dict] = {'GET': AppPermissions.READ_ACTION_DASHBOARD}
    @extend_schema(summary="Compare Metric Snapshots", tags=["Action Dashboard"])
    def get(self, request, region_id: int):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            raise NotFound(detail="Region not found")

        try:
            snapshots_data = self.fetch_analytics_data(region, TemplateCodes.METRIC_SNAPSHOTS)
        except NotFound:
            snapshots_data = {"snapshots": []}

        snapshots = snapshots_data.get("snapshots", [])

        if len(snapshots) < 2:
            return Response({
                "success": True,
                "has_comparison": False,
                "message": "Need at least 2 snapshots for comparison",
                "snapshot_count": len(snapshots)
            })

        from_id = request.query_params.get("from")
        to_id = request.query_params.get("to")

        from_snap, to_snap = None, None

        if from_id and to_id:
            from_snap = next((s for s in snapshots if s["snapshot_id"] == from_id), None)
            to_snap = next((s for s in snapshots if s["snapshot_id"] == to_id), None)
        else:
            from_snap = snapshots[0]
            to_snap = snapshots[-1]

        if not from_snap or not to_snap:
            raise NotFound("Snapshot(s) not found")

        deltas = {}
        for key, to_val in to_snap.get("metrics", {}).items():
            from_val = from_snap.get("metrics", {}).get(key)
            if from_val is not None and isinstance(from_val, (int, float)) and isinstance(to_val, (int, float)):
                delta = to_val - from_val
                delta_pct = round((delta / from_val) * 100, 1) if from_val != 0 else 0

                lower_is_better = key in [
                    'anxiety', 'missing_descriptions', 'missing_media', 'missing_reviews', 'oos_rate'
                ]
                is_improved = (delta < 0) if lower_is_better else (delta > 0)

                deltas[key] = {
                    "from": from_val,
                    "to": to_val,
                    "delta": round(delta, 2),
                    "delta_pct": delta_pct,
                    "improved": is_improved
                }

        return Response({
            "success": True,
            "has_comparison": True,
            "from_snapshot": from_snap,
            "to_snapshot": to_snap,
            "deltas": deltas
        })
