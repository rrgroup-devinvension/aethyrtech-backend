from django.conf import settings
from apps.brand.models import Brand
from apps.users.models import User
from apps.analysis.models import ScrapingLog
import os, json
from rest_framework.views import APIView
from rest_framework.response import Response

class DashboardDataView(APIView):

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
    def get(self, request):
        json_path = os.path.join(settings.MEDIA_ROOT, 'analysis/hp/brand_dashboard_data.json')
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            return Response(data)
        except FileNotFoundError:
            return Response({"error": "File not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class CategoryViewDataView(APIView):

    def get(self, request):
        json_path = os.path.join(settings.MEDIA_ROOT, 'analysis/hp/category_view.json')
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            return Response(data)
        except FileNotFoundError:
            return Response({"error": "File not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class BrandAuditDataView(APIView):

    def get(self, request):
        json_path = os.path.join(settings.MEDIA_ROOT, 'analysis/hp/brand_audit.json')
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            return Response(data)
        except FileNotFoundError:
            return Response({"error": "File not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class ProductCatalogDataView(APIView):

    def get(self, request):
        json_path = os.path.join(settings.MEDIA_ROOT, 'analysis/hp/catalog_data.json')
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            return Response(data)
        except FileNotFoundError:
            return Response({"error": "File not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class ReportTreeDataView(APIView):

    def get(self, request):
        json_path = os.path.join(settings.MEDIA_ROOT, 'analysis/hp/reports_data_tree.json')
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            return Response(data)
        except FileNotFoundError:
            return Response({"error": "File not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class ContentInsightsDataView(APIView):

    def get(self, request):
        json_path = os.path.join(settings.MEDIA_ROOT, 'analysis/hp/content_insights_data.json')
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            return Response(data)
        except FileNotFoundError:
            return Response({"error": "File not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)