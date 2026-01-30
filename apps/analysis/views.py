from django.conf import settings
from apps.brand.models import Brand
from apps.scheduler.models import BrandJsonFile
from apps.scheduler.enums import JsonTemplate
from apps.users.models import User
from apps.analysis.models import ScrapingLog
import os, json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, APIException


def load_json_response(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise NotFound(detail=f"File not found: {file_path}")
    except UnicodeDecodeError as e:
        raise APIException(detail=f"Encoding error: {str(e)}")
    except json.JSONDecodeError as e:
        raise APIException(detail=f"JSON error: {str(e)}")


def serve_brand_template_json(brand, template_name):
    try:
        bj = BrandJsonFile.objects.get(brand=brand, template=template_name)
    except BrandJsonFile.DoesNotExist:
        raise NotFound(detail=f"Data not available for brand {brand.id} and template {template_name}")

    if not bj.file_path:
        raise NotFound(detail=f"Data not available for brand {brand.id} and template {template_name}")

    full_path = os.path.join(settings.MEDIA_ROOT, bj.file_path)
    print(full_path, os.path.exists(full_path))
    if not os.path.exists(full_path):
        raise NotFound(detail=f"Data not available for brand {brand.id} and template {template_name}")
    print("file avaible")
    # File exists — load and return its JSON content
    return load_json_response(full_path)


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
        return Response(serve_brand_template_json(brand, JsonTemplate.BRAND_DASHBOARD.slug), status=200)


class CategoryViewDataView(APIView):
    def get(self, request, brand_id: int):
        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)
        return Response(serve_brand_template_json(brand, JsonTemplate.CATEGORY_VIEW.slug), status=200)


class BrandAuditDataView(APIView):
    def get(self, request, brand_id: int):
        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)
        return Response(serve_brand_template_json(brand, JsonTemplate.BRAND_AUDIT.slug), status=200)


class ProductCatalogDataView(APIView):
    def get(self, request, brand_id: int):
        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)
        sub_type = (request.query_params.get("id") or "")
        catalog_data = serve_brand_template_json(brand, JsonTemplate.CATALOG.slug)
        if not sub_type:
            raise NotFound(detail=f"Data not available for brand {brand.id}")
        catalog_response = catalog_data.get(sub_type, "")
        if not catalog_response:
            raise NotFound(detail=f"Data not available for brand {brand.id} and catalog type {sub_type}")
        return Response(catalog_response, status=200)

class CatalogDetailView(APIView):
    def get(self, request, brand_id: int, product_id: int):
        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)
        products_data = serve_brand_template_json(brand, JsonTemplate.CATALOG.slug)
        print(brand_id, product_id, products_data.keys(), brand.name in products_data.keys())
        if not products_data:
            raise NotFound(detail=f"Catalog data not found")
        brand_data = products_data.get(brand.name)
        if not brand_data:
            raise NotFound(detail=f"Catalog data not found for brand {brand.name}")
        product_response = next((p for p in brand_data if str(p.get("id")) == str(product_id)), None)
        if not product_response:
            raise NotFound(detail=f"Product with id {product_id} not found in brand {brand_id} catalog")
        return Response({"product": product_response}, status=200)

class ReportsDataView(APIView):
    def get(self, request, brand_id: int):
        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)
        # Keep backward compatibility for direct report-tree calls but prefer the unified reports endpoint.
        return Response(serve_brand_template_json(brand, JsonTemplate.REPORTS.slug), status=200)


class ContentInsightsDataView(APIView):
    def get(self, request, brand_id: int):
        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)
        return Response(serve_brand_template_json(brand, JsonTemplate.CONTENT_INSIGHTS.slug), status=200)
