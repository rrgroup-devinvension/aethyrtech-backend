from django.conf import settings
from apps.brand.models import Brand
from apps.users.models import User
from apps.analysis.models import ScrapingLog
import os, json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, APIException


def load_json_response(file_path: str):
    """Helper function to safely load JSON files."""
    try:
        with open(file_path, "r") as f:
            return Response(json.load(f))
    except FileNotFoundError:
        file_name = os.path.basename(file_path)
        raise NotFound(detail=f"Brand data not found")
    except Exception as e:
        raise APIException(detail=str(e))


class DashboardDataView(APIView):
    """Global dashboard data (not brand-specific)."""

    def get(self, request):
        users = User.objects.all()
        brands_count = Brand.objects.count()
        users_count = users.count()
        scraping_logs = ScrapingLog.objects.all()

        return Response({
            "brands_count": brands_count,
            "users_count": users_count,
            "scraping_logs": [
                {
                    "id": log.id,
                    "platform": log.platform,
                    "status": log.status,
                    "products_found": log.products_found,
                    "errors_count": log.errors_count,
                }
                for log in scraping_logs
            ],
        })


class BrandDashboardDataView(APIView):
    """Brand-specific dashboard view."""

    def get(self, request, brand_id: int):
        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)

        folder_name = brand.name.lower().replace(" ", "_")
        json_path = os.path.join(settings.MEDIA_ROOT, f"analysis/{folder_name}/brand_dashboard_data.json")
        return load_json_response(json_path)


class CategoryViewDataView(APIView):
    def get(self, request, brand_id: int):
        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)

        folder_name = brand.name.lower().replace(" ", "_")
        json_path = os.path.join(settings.MEDIA_ROOT, f"analysis/{folder_name}/category_view.json")
        return load_json_response(json_path)


class BrandAuditDataView(APIView):
    def get(self, request, brand_id: int):
        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)

        folder_name = brand.name.lower().replace(" ", "_")
        json_path = os.path.join(settings.MEDIA_ROOT, f"analysis/{folder_name}/brand_audit.json")
        return load_json_response(json_path)


class ProductCatalogDataView(APIView):
    def get(self, request, brand_id: int):
        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)

        folder_name = brand.name.lower().replace(" ", "_")
        json_path = os.path.join(settings.MEDIA_ROOT, f"analysis/{folder_name}/catalog_data.json")
        return load_json_response(json_path)


class ReportTreeDataView(APIView):
    def get(self, request, brand_id: int):
        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)
        folder_name = brand.name.lower().replace(" ", "_")
        json_path = os.path.join(settings.MEDIA_ROOT, f"analysis/{folder_name}/reports_data_tree.json")
        return load_json_response(json_path)


class ContentInsightsDataView(APIView):
    def get(self, request, brand_id: int):
        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)

        folder_name = brand.name.lower().replace(" ", "_")
        json_path = os.path.join(settings.MEDIA_ROOT, f"analysis/{folder_name}/content_insights_data.json")
        return load_json_response(json_path)
