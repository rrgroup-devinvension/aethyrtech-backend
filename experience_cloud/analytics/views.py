import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from core.organizations.models import Brand

logger = logging.getLogger(__name__)

class BrandBaseDataView(APIView):
    """Base view for fetching brand-specific JSON analytics."""
    def get_brand_or_404(self, brand_id):
        try:
            return Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            return None

    def fetch_analytics_data(self, brand, insight_type):
        """
        In the new architecture, this would fetch from S3, 
        a cloud storage bucket, or a pre-computed JSON store.
        """
        return {
            "brand_id": brand.id,
            "brand_name": brand.name,
            "insight_type": insight_type,
            "data": "Data pending backend processing."
        }

class BrandDashboardDataView(BrandBaseDataView):
    @extend_schema(summary="Get Brand Dashboard Data", tags=["Brand Analytics"])
    def get(self, request, brand_id: int):
        brand = self.get_brand_or_404(brand_id)
        if not brand:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)
        return Response(self.fetch_analytics_data(brand, "DASHBOARD"), status=200)

class DashboardPositiveDataView(BrandBaseDataView):
    @extend_schema(summary="Get Brand Positive Data", tags=["Brand Analytics"])
    def get(self, request, brand_id: int):
        brand = self.get_brand_or_404(brand_id)
        if not brand:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)
        return Response(self.fetch_analytics_data(brand, "POSITIVE_DATA"), status=200)

class CROBarriersDataView(BrandBaseDataView):
    @extend_schema(summary="Get CRO Barriers Data", tags=["Brand Analytics"])
    def get(self, request, brand_id: int):
        brand = self.get_brand_or_404(brand_id)
        if not brand:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)
        return Response(self.fetch_analytics_data(brand, "BRAND_GRAPH"), status=200)

class PlpInsightsDataView(BrandBaseDataView):
    @extend_schema(summary="Get PLP Insights Data", tags=["Brand Analytics"])
    def get(self, request, brand_id: int):
        brand = self.get_brand_or_404(brand_id)
        if not brand:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)
        return Response(self.fetch_analytics_data(brand, "PLP_INSIGHTS"), status=200)

class IncentiveInsightsDataView(BrandBaseDataView):
    @extend_schema(summary="Get Incentive Insights Data", tags=["Brand Analytics"])
    def get(self, request, brand_id: int):
        brand = self.get_brand_or_404(brand_id)
        if not brand:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)
        return Response(self.fetch_analytics_data(brand, "INCENTIVE_INSIGHTS"), status=200)

class PdpInsightsDataView(BrandBaseDataView):
    @extend_schema(summary="Get PDP Insights Data", tags=["Brand Analytics"])
    def get(self, request, brand_id: int):
        brand = self.get_brand_or_404(brand_id)
        if not brand:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)
        return Response(self.fetch_analytics_data(brand, "PDP_INSIGHTS"), status=200)

class CategoryDataView(BrandBaseDataView):
    @extend_schema(summary="Get Category Level Data", tags=["Brand Analytics"])
    def get(self, request, brand_id: int):
        brand = self.get_brand_or_404(brand_id)
        if not brand:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)
        return Response(self.fetch_analytics_data(brand, "CATEGORY_DATA"), status=200)

class DataDumpKeywordListView(BrandBaseDataView):
    @extend_schema(summary="Get Data Dump Keywords Data", tags=["Brand Analytics"])
    def get(self, request, brand_id: int):
        brand = self.get_brand_or_404(brand_id)
        if not brand:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)
        return Response(self.fetch_analytics_data(brand, "DATA_DUMP_KEYWORDS"), status=200)
