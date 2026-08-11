import json
import logging
import os
from typing import ClassVar

from django.conf import settings
from django.http import FileResponse
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, NotFound
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from core.authentication.permissions import AppPermissions
from core.llm_providers.services.llm_service import LLMService
from core.organizations.models import Region
from experience_cloud.catalog.models import Location
from experience_cloud.json_generator.models import RegionJsonFile, TemplateCodes

logger = logging.getLogger(__name__)

class RegionBaseDataView(APIView):
    """Base API view providing utility methods to fetch region-specific JSON analytics files from the disk."""
    from shared.serializers import EmptySerializer
    serializer_class = EmptySerializer
    permission_mapping: ClassVar[dict] = {}

    def get_permissions(self):
        """Dynamically resolve permissions based on HTTP method mapping."""
        perms = list(super().get_permissions())

        method = getattr(self.request, 'method', None)
        if method:
            required_perm = self.permission_mapping.get(str(method))
            if required_perm:
                from shared.permissions import HasPermission
                perms.append(HasPermission(required_perm)())

        return perms

    def get_region_or_404(self, region_id):
        """Retrieve a Region object by its primary key, ensuring tenant isolation."""
        from rest_framework.exceptions import PermissionDenied
        try:
            region = Region.objects.get(id=region_id)
            user = self.request.user
            if not user or not user.is_authenticated:
                raise PermissionDenied("Authentication required.")

            is_internal = getattr(getattr(user, 'role', None), 'role_type', None) == 'INTERNAL'
            if getattr(user, 'is_staff', False) or is_internal:
                return region

            # Tenant isolation
            if getattr(user, 'organization_id', None) == region.brand.organization_id:
                return region

            # Fallback for brand-level assigned users
            has_brands = getattr(user, 'brands', None)
            if has_brands and has_brands.filter(id=region.brand.id).exists():
                return region

            raise PermissionDenied("You do not have permission to access data for this region.")
        except Region.DoesNotExist:
            return None

    def fetch_analytics_data(self, region, template_slug):
        """Locate, read, and parse the most recent JSON payload file for a specific region and template."""
        try:
            rjf = RegionJsonFile.objects.filter(region=region, template__template=template_slug).latest("created_at")
        except RegionJsonFile.DoesNotExist as e:
            raise NotFound(detail=f"Data not available for region {region.id} and template {template_slug}") from e

        if not rjf.file_path:
            raise NotFound(detail=f"File path missing for region {region.id} and template {template_slug}")

        full_path = os.path.join(str(settings.MEDIA_ROOT), str(rjf.file_path))

        try:
            with open(full_path, encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError as e:
            raise NotFound(detail=f"File not found on disk: {full_path}") from e
        except UnicodeDecodeError as e:
            raise APIException(detail=f"Encoding error: {e!s}") from e
        except json.JSONDecodeError as e:
            raise APIException(detail=f"JSON error: {e!s}") from e

    def save_analytics_data(self, region, template_slug, data):
        """Save updated JSON data back to the corresponding region's payload file."""
        try:
            rjf = RegionJsonFile.objects.filter(region=region, template__template=template_slug).latest("created_at")
            if not rjf.file_path:
                raise APIException(f"File path missing for region {region.id} and template {template_slug}")

            full_path = os.path.join(str(settings.MEDIA_ROOT), str(rjf.file_path))

            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            return True
        except Exception as e:
            raise APIException(f"Failed to save JSON: {e!s}") from e


class RegionDashboardDataView(RegionBaseDataView):
    """API view for retrieving top-level analytics tailored to a specific region's dashboard."""
    permission_mapping: ClassVar[dict] = {'GET': AppPermissions.READ_EXPERIANCE_DASHBOARD}
    @extend_schema(summary="Get Region Dashboard Data", tags=["Region Analytics"])
    def get(self, request, region_id: int):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            return Response({"error": f"Region with id {region_id} not found"}, status=404)
        return Response(self.fetch_analytics_data(region, TemplateCodes.RISK_DATA), status=200)


class InsightsDataView(RegionBaseDataView):
    """API view for retrieving actionable insights and risk data for a specific region."""
    permission_mapping: ClassVar[dict] = {'GET': AppPermissions.READ_EXPERIANCE_DASHBOARD}
    @extend_schema(summary="Get Insights Data", tags=["Region Analytics"])
    def get(self, request, region_id: int):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            return Response({"error": f"Region with id {region_id} not found"}, status=404)
        return Response({
            "brand_name": region.brand.name,
            "dashboard": self.fetch_analytics_data(region, TemplateCodes.RISK_DATA),
            "insights": self.fetch_analytics_data(region, TemplateCodes.INSIGHTS)
        }, status=200)


class DashboardPositiveDataView(RegionBaseDataView):
    """API view for retrieving positive performance indicators for a specific region."""
    permission_mapping: ClassVar[dict] = {'GET': AppPermissions.READ_GROWTH_LEVER}
    @extend_schema(summary="Get Positive Data", tags=["Region Analytics"])
    def get(self, request, region_id: int):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            return Response({"error": f"Region with id {region_id} not found"}, status=404)
        return Response(self.fetch_analytics_data(region, TemplateCodes.POSITIVE_DATA), status=200)


class CROBarriersDataView(RegionBaseDataView):
    """API view for retrieving Conversion Rate Optimization (CRO) barriers graph data."""
    permission_mapping: ClassVar[dict] = {'GET': AppPermissions.READ_CRO_BARRIERS}
    @extend_schema(summary="Get CRO Barriers Data", tags=["Region Analytics"])
    def get(self, request, region_id: int):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            return Response({"error": f"Region with id {region_id} not found"}, status=404)
        return Response(self.fetch_analytics_data(region, TemplateCodes.BRAND_GRAPH), status=200)


class PlpInsightsDataView(RegionBaseDataView):
    """API view for retrieving Product Listing Page (PLP) insights."""
    permission_mapping: ClassVar[dict] = {'GET': AppPermissions.READ_PLP_INSIGHTS}
    @extend_schema(summary="Get PLP Insights Data", tags=["Region Analytics"])
    def get(self, request, region_id: int):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            return Response({"error": f"Region with id {region_id} not found"}, status=404)
        return Response(self.fetch_analytics_data(region, TemplateCodes.PLP_INSIGHTS), status=200)


class IncentiveInsightsDataView(RegionBaseDataView):
    """API view for retrieving pricing and promotional incentive insights."""
    permission_mapping: ClassVar[dict] = {'GET': AppPermissions.READ_INCENTIVE_INSIGHTS}
    @extend_schema(summary="Get Incentive Insights Data", tags=["Region Analytics"])
    def get(self, request, region_id: int):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            return Response({"error": f"Region with id {region_id} not found"}, status=404)
        return Response(self.fetch_analytics_data(region, TemplateCodes.INCENTIVE_INSIGHTS), status=200)


class PdpInsightsDataView(RegionBaseDataView):
    """API view for retrieving Product Detail Page (PDP) insights."""
    permission_mapping: ClassVar[dict] = {'GET': AppPermissions.READ_PDP_INSIGHTS}
    @extend_schema(summary="Get PDP Insights Data", tags=["Region Analytics"])
    def get(self, request, region_id: int):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            return Response({"error": f"Region with id {region_id} not found"}, status=404)
        return Response(self.fetch_analytics_data(region, TemplateCodes.PDP_INSIGHTS), status=200)


class ReviewsInsightsDataView(RegionBaseDataView):
    """API view for retrieving customer review insights and sentiment analysis."""
    permission_mapping: ClassVar[dict] = {'GET': AppPermissions.READ_REVIEWS_INSIGHTS}
    @extend_schema(summary="Get Reviews Insights Data", tags=["Region Analytics"])
    def get(self, request, region_id: int):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            return Response({"error": f"Region with id {region_id} not found"}, status=404)
        return Response(self.fetch_analytics_data(region, TemplateCodes.REVIEWS_INSIGHTS), status=200)


class CategoryDataView(RegionBaseDataView):
    """API view for retrieving category-level performance views."""
    permission_mapping: ClassVar[dict] = {'GET': AppPermissions.READ_GAP_LANDSCAPES}
    @extend_schema(summary="Get Category Data", tags=["Region Analytics"])
    def get(self, request, region_id: int):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            return Response({"error": f"Region with id {region_id} not found"}, status=404)
        return Response(self.fetch_analytics_data(region, TemplateCodes.CATEGORY_VIEW), status=200)


class BrandAuditDataView(RegionBaseDataView):
    """API view for retrieving comprehensive brand audit metrics across categories."""
    permission_mapping: ClassVar[dict] = {'GET': AppPermissions.READ_PLATFORM_AUDIT}
    @extend_schema(summary="Get Brand Audit Data", tags=["Region Analytics"])
    def get(self, request, region_id: int):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            return Response({"error": f"Region with id {region_id} not found"}, status=404)
        return Response({
            "category": self.fetch_analytics_data(region, TemplateCodes.CATEGORY_VIEW),
            "dashboard": self.fetch_analytics_data(region, TemplateCodes.INSIGHTS),
            "brands_list": [
                region.brand.name,
                *region.competitors.filter(is_active=True).values_list('name', flat=True)
            ]
        }, status=200)


class ContentInsightsDataView(RegionBaseDataView):
    """API view for retrieving insights on content effectiveness and completeness."""
    permission_mapping: ClassVar[dict] = {'GET': AppPermissions.READ_PRODUCT_CATALOG}
    @extend_schema(summary="Get Content Insights Data", tags=["Region Analytics"])
    def get(self, request, region_id: int):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            return Response({"error": f"Region with id {region_id} not found"}, status=404)
        return Response(self.fetch_analytics_data(region, "content_insights"), status=200)


class ProductCatalogDataView(RegionBaseDataView):
    """API view for retrieving the raw product catalog data for a specific region."""
    permission_mapping: ClassVar[dict] = {'GET': AppPermissions.READ_PRODUCT_CATALOG}
    @extend_schema(summary="Get Product Catalog Data", tags=["Region Analytics"])
    def get(self, request, region_id: int):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            return Response({"error": f"Region with id {region_id} not found"}, status=404)

        sub_type = (request.query_params.get("id") or "")
        catalog_data = self.fetch_analytics_data(region, TemplateCodes.CATALOG)

        if not sub_type:
            raise NotFound(detail="Catalog filter 'id' not provided")

        catalog_response = catalog_data.get(sub_type, "")
        return Response(catalog_response, status=200)


class CatalogDetailView(RegionBaseDataView):
    """API view for retrieving highly detailed information and keywords for a specific product."""
    permission_mapping: ClassVar[dict] = {'GET': AppPermissions.READ_PRODUCT_CATALOG}
    @extend_schema(summary="Get Catalog Detail Data", tags=["Region Analytics"])
    def get(self, request, region_id: int, product_id: str):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            return Response({"error": f"Region with id {region_id} not found"}, status=404)

        products_data = self.fetch_analytics_data(region, TemplateCodes.CATALOG)

        # Legacy assumed brand name as the top-level key. Verify this matches the new structure.
        brand_name = region.brand.name
        brand_data = products_data.get(brand_name)
        if not brand_data:
            raise NotFound(detail=f"Catalog data not found for brand {brand_name}")

        product_response = next((p for p in brand_data if str(p.get("id")) == product_id), None)
        if not product_response:
            raise NotFound(detail=f"Product with id {product_id} not found in region {region_id} catalog")

        keywords_data = self.fetch_analytics_data(region, TemplateCodes.KEYWORD_COUNTS)
        product_title = product_response.get("product_title")
        filtered_keywords = {}

        if keywords_data and product_title:
            for platform, products in keywords_data.items():
                if product_title in products:
                    filtered_keywords[platform] = {
                        product_title: products[product_title]
                    }

        return Response({"product": product_response, "keywords": filtered_keywords}, status=200)


class ReportsDataView(RegionBaseDataView):
    """API view for retrieving geographical reports and pincode availability data."""
    permission_mapping: ClassVar[dict] = {'GET': AppPermissions.READ_AUDIENCE_AUDIT}
    @extend_schema(summary="Get Reports Data", tags=["Region Analytics"])
    def get(self, request, region_id: int):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            return Response({"error": f"Region with id {region_id} not found"}, status=404)

        locations = Location.objects.filter(region=region, is_active=True)
        pincodes = []
        for loc in locations:
            if loc.lat and loc.lng and loc.pincode:
                pincodes.append({
                    "lat": float(loc.lat),
                    "lng": float(loc.lng),
                    "area": loc.address or "Unknown",
                    "pincode": loc.pincode
                })

        return Response({
            "reports": self.fetch_analytics_data(region, TemplateCodes.CARTESIAN_PRODUCTS_PINCODES),
            "pincodes": pincodes
        }, status=200)


class GenerateContentView(RegionBaseDataView):
    """API view to trigger the LLM service for generating SEO-optimized product content."""
    permission_mapping: ClassVar[dict] = {'POST': AppPermissions.GENERATE_CONTENT}
    @extend_schema(summary="Generate Content for Product", tags=["Region Analytics"])
    def post(self, request):
        """Handle POST request."""
        product_id = request.data.get("product_id")
        section = request.data.get("section")
        region_id = request.data.get("region_id")

        if not product_id or not section or not region_id:
            raise APIException("product_id, region_id and section required")

        region = self.get_region_or_404(region_id)
        if not region:
            raise NotFound("Region not found")

        catalog = self.fetch_analytics_data(region, TemplateCodes.CATALOG)
        brand_name = region.brand.name
        brand_data = catalog.get(brand_name, [])

        product = next((p for p in brand_data if str(p.get("id")) == str(product_id)), None)
        if not product:
            raise NotFound("Product not found")

        title = product.get("product_title", "N/A")
        detail_data = product.get("detail_data", {})
        description = detail_data.get("description", "No description available.")
        bullets = "\n".join(detail_data.get("bullets", [])) or "No features available."

        # Normally we'd fetch keywords from the platform catalog keywords
        # For simplicity in migration, just a placeholder if keywords are not supplied
        keywords_text = "N/A"

        prompt = f"""
You are an expert E-commerce Copywriter and Senior Brand Manager.

### INPUT DATA
Brand: {brand_name}
Product Title: {title}
Current Description: {description}
Current Features:
{bullets}

Priority:
- Preserve technical facts exactly
- Do not invent specifications

### SEO KEYWORDS
Available Keywords: [{keywords_text}]

Rules:
1. Use only relevant keywords.
2. Avoid keyword stuffing.
3. Keep natural readability.
"""
        if section == "features":
            prompt += (
                "\nGenerate 5-6 bullet features:\n"
                "- Total words: 100-300\n"
                "- Each bullet starts with **Feature Name:**\n"
                "- Professional tone\n"
                "- Keywords integrated naturally\n"
            )
        else:
            prompt += (
                "\nGenerate description:\n"
                "- 100-300 words\n"
                "- No bullet points\n"
                "- British English tone\n"
                "- Professional yet engaging\n"
            )

        prompt += "\nReturn ONLY final content.\n"

        # Initialize LLMService using the factory method
        service = LLMService.get_service()
        messages = [{'role': 'user', 'content': prompt}]
        results = service.generate_content(
            messages=messages,
            action="CONTENT_GENERATION",
            brand_id=region.brand.id,
            brand_name=region.brand.name
        )

        return Response({"content": results})


class UpdateProductContentView(RegionBaseDataView):
    """API view to save updated product content directly back into the region's JSON catalog file."""
    permission_mapping: ClassVar[dict] = {'POST': AppPermissions.UPDATE_PRODUCTS}
    @extend_schema(summary="Update Product Content JSON", tags=["Region Analytics"])
    def post(self, request):
        """Handle POST request."""
        product_id = request.data.get("product_id")
        region_id = request.data.get("region_id")
        section = request.data.get("section")
        content = request.data.get("content")

        region = self.get_region_or_404(region_id)
        if not region:
            raise NotFound("Region not found")

        catalog = self.fetch_analytics_data(region, TemplateCodes.CATALOG)
        brand_name = region.brand.name
        brand_data = catalog.get(brand_name, [])

        product = next((p for p in brand_data if str(p.get("id")) == str(product_id)), None)
        if not product:
            raise NotFound("Product not found")

        if section == "features":
            product.setdefault("detail_data", {})["bullets"] = content.split("\n")
        else:
            product.setdefault("detail_data", {})["description"] = content

        try:
            rjf = RegionJsonFile.objects.filter(
                region=region, template__template=TemplateCodes.CATALOG
            ).latest("created_at")
            full_path = os.path.join(str(settings.MEDIA_ROOT), str(rjf.file_path))
            with open(full_path, "w", encoding="utf-8") as f:
                json.dump(catalog, f, indent=4)
        except Exception as e:
            raise APIException(f"Failed to save JSON: {e!s}") from e

        return Response({"success": True})


class AnalyticsDownloadViewSet(ViewSet, RegionBaseDataView):
    """ViewSet to handle distinct file downloads for different templates."""

    # Optionally, restrict access base on permissions

    def _download_file(self, region_id, template_code):
        region = self.get_region_or_404(region_id)
        if not region:
            raise NotFound("Region not found or permission denied.")

        try:
            rjf = RegionJsonFile.objects.filter(region=region, template__template=template_code).latest("created_at")
        except RegionJsonFile.DoesNotExist as e:
            raise NotFound(detail=f"Data not available for region {region.id} and template {template_code}") from e

        if not rjf.file_path:
            raise NotFound(detail=f"File path missing for region {region.id} and template {template_code}")

        full_path = os.path.join(str(settings.MEDIA_ROOT), str(rjf.file_path))
        if not os.path.exists(full_path):
            raise NotFound(detail="File not found on disk.")

        # Determine content type based on extension
        ext = os.path.splitext(full_path)[1].lower()
        content_type = 'application/json'
        if ext == '.csv':
            content_type = 'text/csv'
        elif ext == '.pdf':
            content_type = 'application/pdf'
        elif ext == '.html':
            content_type = 'text/html'

        return FileResponse(
            open(full_path, 'rb'),
            content_type=content_type,
            as_attachment=True,
            filename=os.path.basename(full_path)
        )

    @extend_schema(summary="Download PLP Keyword Opportunities", tags=["Region Analytics Downloads"])
    @action(detail=False, methods=['get'], url_path='download/plp-keyword-opportunities')
    def download_plp_keyword_opportunities(self, request):
        """Download PLP Keyword Opportunities data as CSV."""
        region_id = request.query_params.get("region_id")
        return self._download_file(region_id, TemplateCodes.PLP_KEYWORD_OPPORTUNITIES)

    @extend_schema(summary="Download PDP Content Audit", tags=["Region Analytics Downloads"])
    @action(detail=False, methods=['get'], url_path='download/pdp-content-audit')
    def download_pdp_content_audit(self, request):
        """Download PDP Content Audit data as CSV."""
        region_id = request.query_params.get("region_id")
        return self._download_file(region_id, TemplateCodes.PDP_CONTENT_AUDIT)

    @extend_schema(summary="Download Discount Opportunities", tags=["Region Analytics Downloads"])
    @action(detail=False, methods=['get'], url_path='download/discount-opportunities')
    def download_discount_opportunities(self, request):
        """Download Discount Opportunities data as CSV."""
        region_id = request.query_params.get("region_id")
        return self._download_file(region_id, TemplateCodes.DISCOUNT_OPPORTUNITIES)

    @extend_schema(summary="Download Alerts Reviews Report", tags=["Region Analytics Downloads"])
    @action(detail=False, methods=['get'], url_path='download/alerts-reviews-report')
    def download_alerts_reviews_report(self, request):
        """Download Alerts Reviews Report data as CSV."""
        region_id = request.query_params.get("region_id")
        return self._download_file(region_id, TemplateCodes.ALERTS_REVIEWS_REPORT)

    @extend_schema(summary="Download Topic Negative Reviews", tags=["Region Analytics Downloads"])
    @action(detail=False, methods=['get'], url_path='download/topic-negative-reviews')
    def download_topic_negative_reviews(self, request):
        """Download Topic Negative Reviews data as CSV."""
        region_id = request.query_params.get("region_id")
        return self._download_file(region_id, TemplateCodes.TOPIC_NEGATIVE_REVIEWS)

    @extend_schema(summary="Download Product Deepdive Data", tags=["Region Analytics Downloads"])
    @action(detail=False, methods=['get'], url_path='download/product-deepdive-data')
    def download_product_deepdive_data(self, request):
        """Download product deepdive data as CSV."""
        region_id = request.query_params.get("region_id")
        return self._download_file(region_id, TemplateCodes.PRODUCT_DEEPDIVE_DATA)

