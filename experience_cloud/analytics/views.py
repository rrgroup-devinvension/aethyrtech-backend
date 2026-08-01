import json
import logging
import os

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import APIException, NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from core.llm_providers.services.llm_service import LLMService
from core.organizations.models import Brand, Region
from core.users.models import User
from experience_cloud.json_generator.models import RegionJsonFile

logger = logging.getLogger(__name__)

class RegionBaseDataView(APIView):
    """Base API view providing utility methods to fetch region-specific JSON analytics files from the disk."""
    from shared.serializers import EmptySerializer
    serializer_class = EmptySerializer
    def get_region_or_404(self, region_id):
        """Retrieve a Region object by its primary key, or return None if it does not exist."""
        try:
            return Region.objects.get(id=region_id)
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


class DashboardDataView(APIView):
    """API view for retrieving high-level global dashboard metrics."""
    from shared.serializers import EmptySerializer
    serializer_class = EmptySerializer

    @extend_schema(summary="Get Global Dashboard Data", tags=["Global Analytics"])
    def get(self, request):
        """Retrieve aggregated global platform statistics like total users and brands."""
        users_count = User.objects.count()
        brands_count = Brand.objects.count()

        return Response({
            "brands_count": brands_count,
            "users_count": users_count,
            "scraping_logs": [] # Left blank until scraping logs logic is defined in experience_cloud
        })


class RegionDashboardDataView(RegionBaseDataView):
    """API view for retrieving top-level analytics tailored to a specific region's dashboard."""
    @extend_schema(summary="Get Region Dashboard Data", tags=["Region Analytics"])
    def get(self, request, region_id: int):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            return Response({"error": f"Region with id {region_id} not found"}, status=404)
        return Response(self.fetch_analytics_data(region, "risk_data"), status=200)


class InsightsDataView(RegionBaseDataView):
    """API view for retrieving actionable insights and risk data for a specific region."""
    @extend_schema(summary="Get Insights Data", tags=["Region Analytics"])
    def get(self, request, region_id: int):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            return Response({"error": f"Region with id {region_id} not found"}, status=404)
        return Response({
            "brand_name": region.brand.name,
            "dashboard": self.fetch_analytics_data(region, "risk_data"),
            "insights": self.fetch_analytics_data(region, "insights")
        }, status=200)


class DashboardPositiveDataView(RegionBaseDataView):
    """API view for retrieving positive performance indicators for a specific region."""
    @extend_schema(summary="Get Positive Data", tags=["Region Analytics"])
    def get(self, request, region_id: int):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            return Response({"error": f"Region with id {region_id} not found"}, status=404)
        return Response(self.fetch_analytics_data(region, "positive_data"), status=200)


class CROBarriersDataView(RegionBaseDataView):
    """API view for retrieving Conversion Rate Optimization (CRO) barriers graph data."""
    @extend_schema(summary="Get CRO Barriers Data", tags=["Region Analytics"])
    def get(self, request, region_id: int):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            return Response({"error": f"Region with id {region_id} not found"}, status=404)
        return Response(self.fetch_analytics_data(region, "brand_graph"), status=200)


class PlpInsightsDataView(RegionBaseDataView):
    """API view for retrieving Product Listing Page (PLP) insights."""
    @extend_schema(summary="Get PLP Insights Data", tags=["Region Analytics"])
    def get(self, request, region_id: int):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            return Response({"error": f"Region with id {region_id} not found"}, status=404)
        return Response(self.fetch_analytics_data(region, "plp_insights"), status=200)


class IncentiveInsightsDataView(RegionBaseDataView):
    """API view for retrieving pricing and promotional incentive insights."""
    @extend_schema(summary="Get Incentive Insights Data", tags=["Region Analytics"])
    def get(self, request, region_id: int):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            return Response({"error": f"Region with id {region_id} not found"}, status=404)
        return Response(self.fetch_analytics_data(region, "incentive_insights"), status=200)


class PdpInsightsDataView(RegionBaseDataView):
    """API view for retrieving Product Detail Page (PDP) insights."""
    @extend_schema(summary="Get PDP Insights Data", tags=["Region Analytics"])
    def get(self, request, region_id: int):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            return Response({"error": f"Region with id {region_id} not found"}, status=404)
        return Response(self.fetch_analytics_data(region, "pdp_insights"), status=200)


class ReviewsInsightsDataView(RegionBaseDataView):
    """API view for retrieving customer review insights and sentiment analysis."""
    @extend_schema(summary="Get Reviews Insights Data", tags=["Region Analytics"])
    def get(self, request, region_id: int):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            return Response({"error": f"Region with id {region_id} not found"}, status=404)
        return Response(self.fetch_analytics_data(region, "reviews_insights"), status=200)


class CategoryDataView(RegionBaseDataView):
    """API view for retrieving category-level performance views."""
    @extend_schema(summary="Get Category Data", tags=["Region Analytics"])
    def get(self, request, region_id: int):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            return Response({"error": f"Region with id {region_id} not found"}, status=404)
        return Response(self.fetch_analytics_data(region, "category_view"), status=200)


class BrandAuditDataView(RegionBaseDataView):
    """API view for retrieving comprehensive brand audit metrics across categories."""
    @extend_schema(summary="Get Brand Audit Data", tags=["Region Analytics"])
    def get(self, request, region_id: int):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            return Response({"error": f"Region with id {region_id} not found"}, status=404)
        return Response({
            "category": self.fetch_analytics_data(region, "category_view"),
            "dashboard": self.fetch_analytics_data(region, "insights")
        }, status=200)


class ContentInsightsDataView(RegionBaseDataView):
    """API view for retrieving insights on content effectiveness and completeness."""
    @extend_schema(summary="Get Content Insights Data", tags=["Region Analytics"])
    def get(self, request, region_id: int):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            return Response({"error": f"Region with id {region_id} not found"}, status=404)
        return Response(self.fetch_analytics_data(region, "content_insights"), status=200)


class ProductCatalogDataView(RegionBaseDataView):
    """API view for retrieving the raw product catalog data for a specific region."""
    @extend_schema(summary="Get Product Catalog Data", tags=["Region Analytics"])
    def get(self, request, region_id: int):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            return Response({"error": f"Region with id {region_id} not found"}, status=404)

        sub_type = (request.query_params.get("id") or "")
        catalog_data = self.fetch_analytics_data(region, "catalog")

        if not sub_type:
            raise NotFound(detail="Catalog filter 'id' not provided")

        catalog_response = catalog_data.get(sub_type, "")
        return Response(catalog_response, status=200)


class CatalogDetailView(RegionBaseDataView):
    """API view for retrieving highly detailed information and keywords for a specific product."""
    @extend_schema(summary="Get Catalog Detail Data", tags=["Region Analytics"])
    def get(self, request, region_id: int, product_id: str):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            return Response({"error": f"Region with id {region_id} not found"}, status=404)

        products_data = self.fetch_analytics_data(region, "catalog")

        # Legacy assumed brand name as the top-level key. Verify this matches the new structure.
        brand_name = region.brand.name
        brand_data = products_data.get(brand_name)
        if not brand_data:
            raise NotFound(detail=f"Catalog data not found for brand {brand_name}")

        product_response = next((p for p in brand_data if str(p.get("id")) == product_id), None)
        if not product_response:
            raise NotFound(detail=f"Product with id {product_id} not found in region {region_id} catalog")

        keywords_data = self.fetch_analytics_data(region, "keyword_counts")
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
    @extend_schema(summary="Get Reports Data", tags=["Region Analytics"])
    def get(self, request, region_id: int):
        """Handle GET request."""
        region = self.get_region_or_404(region_id)
        if not region:
            return Response({"error": f"Region with id {region_id} not found"}, status=404)

        # Keep backward compatibility for pincodes
        return Response({
            "reports": self.fetch_analytics_data(region, "cartesian_products_pincodes"),
            "pincodes": [
                { "lat": 28.6517, "lng": 77.1906, "area": "Karol Bagh", "pincode": "110005" },
                { "lat": 28.4089, "lng": 77.3178, "area": "Faridabad Sector 6", "pincode": "121006" },
                { "lat": 28.6503, "lng": 77.1194, "area": "Rajouri Garden", "pincode": "110027" },
                # Truncated for brevity, normally this would be a full list or loaded from DB
            ]
        }, status=200)


class GenerateContentView(RegionBaseDataView):
    """API view to trigger the LLM service for generating SEO-optimized product content."""
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

        catalog = self.fetch_analytics_data(region, "catalog")
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

        catalog = self.fetch_analytics_data(region, "catalog")
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
            rjf = RegionJsonFile.objects.filter(region=region, template__template="catalog").latest("created_at")
            full_path = os.path.join(str(settings.MEDIA_ROOT), str(rjf.file_path))
            with open(full_path, "w", encoding="utf-8") as f:
                json.dump(catalog, f, indent=4)
        except Exception as e:
            raise APIException(f"Failed to save JSON: {e!s}") from e

        return Response({"success": True})

