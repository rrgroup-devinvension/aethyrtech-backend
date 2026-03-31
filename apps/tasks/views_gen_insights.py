from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsStaffOrReadOnly
from .services.generate_cxo_insights import generate_cxo_insights
from .services.generate_plp_insights import generate_plp_insights
from .services.generate_pdp_insights import generate_pdp_insights
from .services.generate_incentive_insights import generate_incentive_insights
from .services.generate_brand_graph import generate_brand_graph
from .services.generate_reviews_insights import generate_reviews_insights
from .services.generate_risk_data import generate_risk_data
from .services.generate_positive_data import generate_positive_data
from apps.brand.models import Brand
import logging

logger = logging.getLogger(__name__)


class BaseGenInsightsView(APIView):
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]

    def get_brand(self, request):
        brand_id = request.data.get('brandId')

        if not brand_id:
            return None, Response(
                {"error": "brandId is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            brand = Brand.objects.get(id=brand_id, is_deleted=False)
            return brand, None
        except Brand.DoesNotExist:
            return None, Response(
                {"error": "Invalid brandId"},
                status=status.HTTP_404_NOT_FOUND
            )
        
class GenInsightsRegenerateView(BaseGenInsightsView):

    def post(self, request):
        brand, error = self.get_brand(request)
        if error:
            return error

        try:
            # 👉 CALL YOUR SERVICE / LOGIC HERE
            # example:
            generate_cxo_insights(brand)

            return Response({
                "message": f"Insights regenerated for {brand.name}"
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Regenerate failed")
            return Response({
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class GenInsightsBrandGraphView(BaseGenInsightsView):

    def post(self, request):
        brand, error = self.get_brand(request)
        if error:
            return error

        try:
            generate_brand_graph(brand)
            return Response({
                "message": f"Brand graph generated for {brand.name}"
            })
        except Exception as e:
            logger.exception("Graph failed")
            return Response({"error": str(e)}, status=500)
        

class GenInsightsRiskView(BaseGenInsightsView):

    def post(self, request):
        brand, error = self.get_brand(request)
        if error:
            return error

        try:
            generate_risk_data(brand)
            return Response({
                "message": f"Risk data generated for {brand.name}"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)

class GenInsightsPositiveView(BaseGenInsightsView):

    def post(self, request):
        brand, error = self.get_brand(request)
        if error:
            return error

        try:
            generate_positive_data(brand)
            return Response({
                "message": f"Positive data generated for {brand.name}"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)

class GenInsightsReviewsView(BaseGenInsightsView):

    def post(self, request):
        brand, error = self.get_brand(request)
        if error:
            return error

        try:
            generate_reviews_insights(brand)
            return Response({
                "message": f"Reviews processed for {brand.name}"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)

class GenInsightsPlpView(BaseGenInsightsView):

    def post(self, request):
        brand, error = self.get_brand(request)
        if error:
            return error

        try:
            generate_plp_insights(brand)
            return Response({
                "message": f"PLP insights generated for {brand.name}"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class GenInsightsPdpView(BaseGenInsightsView):

    def post(self, request):
        brand, error = self.get_brand(request)
        if error:
            return error

        try:
            generate_pdp_insights(brand)
            return Response({
                "message": f"PDP insights generated for {brand.name}"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class GenInsightsIncentiveView(BaseGenInsightsView):

    def post(self, request):
        brand, error = self.get_brand(request)
        if error:
            return error

        try:
            generate_incentive_insights(brand)
            return Response({
                "message": f"Incentive insights generated for {brand.name}"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)




