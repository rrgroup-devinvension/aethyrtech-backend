from django.conf import settings
from apps.brand.models import Brand
from apps.scheduler.models import BrandJsonFile
from apps.category.models import CategoryKeyword
from apps.scheduler.enums import JsonTemplate
from apps.users.models import User
from apps.analysis.models import ScrapingLog
import os, json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, APIException
from apps.analysis.services.llm_service import LLMService


from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes


import os
from django.conf import settings
from django.http import FileResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, APIException


@api_view(["GET"])
@permission_classes([AllowAny])
def download_brand_file(request):
    try:
        brand_id = request.GET.get("brand_id")
        template = request.GET.get("template")
        file_type = request.GET.get("type", "json")  # json / csv / html
        prefix = request.GET.get("prefix")  # optional

        if not brand_id or not template:
            return Response({"error": "brand_id and template are required"}, status=400)

        # ===============================
        # GET BRAND + JSON ENTRY
        # ===============================
        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            raise NotFound("Brand not found")

        try:
            bj = BrandJsonFile.objects.get(brand=brand, template=template)
        except BrandJsonFile.DoesNotExist:
            raise NotFound("Data not available")

        if not bj.file_path:
            raise NotFound("File path not found")

        # ===============================
        # BASE FOLDER
        # ===============================
        base_folder = os.path.dirname(os.path.join(settings.MEDIA_ROOT, bj.file_path))

        # Extract timestamp from main JSON
        filename = os.path.basename(bj.file_path)
        timestamp = filename.replace(".json", "").split("-")[-1]

        # ===============================
        # CASE 1: JSON FILE
        # ===============================
        if file_type == "json":
            full_path = os.path.join(settings.MEDIA_ROOT, bj.file_path)

        else:
            # ===============================
            # CASE 2: EXTRA FILE (CSV / HTML)
            # ===============================
            if not prefix:
                return Response({"error": "prefix required for non-json files"}, status=400)

            # Construct expected filename
            expected_file = f"{prefix}-{timestamp}.{file_type}"
            full_path = os.path.join(base_folder, expected_file)

        # ===============================
        # VALIDATION
        # ===============================
        if not os.path.exists(full_path):
            raise NotFound(f"File not found: {full_path}")

        # ===============================
        # RETURN FILE
        # ===============================
        response = FileResponse(open(full_path, "rb"))
        if file_type == "html":
            response["Content-Disposition"] = f'inline; filename="{os.path.basename(full_path)}"'
        else:
            response["Content-Disposition"] = f'attachment; filename="{os.path.basename(full_path)}"'

        return response

    except Exception as e:
        raise APIException(str(e))

@api_view(['POST'])
@permission_classes([AllowAny])
def contact_api(request):
    try:
        name = request.data.get('name')
        email = request.data.get('email')
        mobile = request.data.get('mobile')
        message = request.data.get('message')

        subject = f"New Contact Request from {name}"

        body = f"""
        Name: {name}
        Email: {email}
        Mobile: {mobile}

        Message:
        {message}
        """

        send_mail(
            subject,
            body,
            settings.EMAIL_HOST_USER,   # from
            ['Aethyrtech@aethyrtech.AI'],  # to
            fail_silently=False,
        )

        return Response({"success": True, "message": "Email sent successfully"})

    except Exception as e:
        return Response({"success": False, "error": str(e)}, status=500)
    
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
        return Response(serve_brand_template_json(brand, JsonTemplate.RISK_DATA.slug), status=200)


class InsightsDataView(APIView):
    """Brand-specific dashboard view."""

    def get(self, request, brand_id: int):
        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)
        return Response({
            "dashboard": serve_brand_template_json(brand, JsonTemplate.RISK_DATA.slug),
            "insights": serve_brand_template_json(brand, JsonTemplate.INSIGHTS.slug)
        }, status=200)


class DashboardPositiveDataView(APIView):
    """Brand-specific dashboard view."""

    def get(self, request, brand_id: int):
        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)
        return Response(serve_brand_template_json(brand, JsonTemplate.POSITIVE_DATA.slug), status=200)


class CROBarriersDataView(APIView):
    """Brand-specific dashboard view."""

    def get(self, request, brand_id: int):
        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)
        return Response(serve_brand_template_json(brand, JsonTemplate.BRAND_GRAPH.slug), status=200)

class PlpInsightsDataView(APIView):
    """Brand-specific PLP insights view."""

    def get(self, request, brand_id: int):
        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)
        return Response(serve_brand_template_json(brand, JsonTemplate.PLP_INSIGHTS.slug), status=200)


class IncentiveInsightsDataView(APIView):
    """Brand-specific dashboard view."""

    def get(self, request, brand_id: int):
        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)
        return Response(serve_brand_template_json(brand, JsonTemplate.INCENTIVE_INSIGHTS.slug), status=200)


class PdpInsightsDataView(APIView):
    """Brand-specific dashboard view."""

    def get(self, request, brand_id: int):
        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)
        return Response(serve_brand_template_json(brand, JsonTemplate.PDP_INSIGHTS.slug), status=200)


class ReviewsInsightsDataView(APIView):
    """Brand-specific dashboard view."""

    def get(self, request, brand_id: int):
        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)
        return Response(serve_brand_template_json(brand, JsonTemplate.REVIEWS_INSIGHTS.slug), status=200)


class CategoryDataView(APIView):
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
        return Response({
            "category": serve_brand_template_json(brand, JsonTemplate.CATEGORY_VIEW.slug),
            "dashboard":  serve_brand_template_json(brand, JsonTemplate.INSIGHTS.slug)
        }, status=200)


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
        keywords_data = serve_brand_template_json(brand, JsonTemplate.KEYWORD_COUNTS.slug)
        product_title = product_response.get("product_title")
        filtered_keywords = {}
        if keywords_data and product_title:
            for platform, products in keywords_data.items():
                if product_title in products:
                    filtered_keywords[platform] = {
                        product_title: products[product_title]
                    }
        return Response({"product": product_response,"keywords": filtered_keywords}, status=200)

class ReportsDataView(APIView):
    def get(self, request, brand_id: int):
        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)
        # Keep backward compatibility for direct report-tree calls but prefer the unified reports endpoint.
        return Response({
            "reports": serve_brand_template_json(brand, JsonTemplate.CARTESIAN_PRODUCTS_PINCODES.slug),
            "pincodes": [
  { "lat": 28.6517, "lng": 77.1906, "area": "Karol Bagh", "pincode": "110005" },
  { "lat": 28.4089, "lng": 77.3178, "area": "Faridabad Sector 6", "pincode": "121006" },
  { "lat": 28.6503, "lng": 77.1194, "area": "Rajouri Garden", "pincode": "110027" },
  { "lat": 28.5485, "lng": 76.9855, "area": "Chhawla", "pincode": "110071" },
  { "lat": 28.4305, "lng": 77.3056, "area": "Faridabad NIT", "pincode": "121004" },
  { "lat": 28.7092, "lng": 77.1543, "area": "Pitampura", "pincode": "110034" },
  { "lat": 28.5638, "lng": 77.2609, "area": "East of Kailash", "pincode": "110065" },
  { "lat": 28.6692, "lng": 77.2315, "area": "Chandni Chowk", "pincode": "110006" },
  { "lat": 28.5632, "lng": 77.054, "area": "Dwarka", "pincode": "110075" },
  { "lat": 28.58, "lng": 77.195, "area": "Netaji Nagar", "pincode": "110023" },
  { "lat": 28.4089, "lng": 77.3178, "area": "Faridabad Sector 15", "pincode": "121001" },
  { "lat": 28.5892, "lng": 77.046, "area": "Janakpuri", "pincode": "110045" },
  { "lat": 28.5381, "lng": 77.1971, "area": "Hauz Khas", "pincode": "110016" },
  { "lat": 28.4595, "lng": 77.0266, "area": "Faridabad Sector 12", "pincode": "121012" },
  { "lat": 28.6565, "lng": 77.14, "area": "Tilak Nagar", "pincode": "110018" },
  { "lat": 28.5845, "lng": 77.1881, "area": "Chanakyapuri", "pincode": "110021" },
  { "lat": 28.7005, "lng": 77.1678, "area": "Ashok Vihar", "pincode": "110035" },
  { "lat": 28.7288, "lng": 77.1068, "area": "Rohini", "pincode": "110085" },
  { "lat": 28.6842, "lng": 77.288, "area": "Shahdara", "pincode": "110032" },
  { "lat": 28.4595, "lng": 77.0266, "area": "Gurgaon", "pincode": "122001" },
  { "lat": 28.6905, "lng": 77.2647, "area": "Seelampur", "pincode": "110053" },
  { "lat": 28.6304, "lng": 77.2177, "area": "Connaught Place", "pincode": "110001" },
  { "lat": 28.6355, "lng": 77.2697, "area": "Laxmi Nagar", "pincode": "110092" },
  { "lat": 28.626, "lng": 77.309, "area": "Mayur Vihar Phase 1", "pincode": "110091" },
  { "lat": 28.4973, "lng": 77.088, "area": "DLF Phase 1", "pincode": "122010" },
  { "lat": 28.5165, "lng": 77.232, "area": "Saket", "pincode": "110062" },
  { "lat": 28.6528, "lng": 77.2848, "area": "Krishna Nagar", "pincode": "110051" },
  { "lat": 28.523, "lng": 77.2145, "area": "Malviya Nagar", "pincode": "110017" },
  { "lat": 28.619, "lng": 76.997, "area": "Najafgarh", "pincode": "110072" },
  { "lat": 28.5245, "lng": 77.077, "area": "DLF Phase 2", "pincode": "122011" },
  { "lat": 28.9931, "lng": 77.0151, "area": "Sonipat", "pincode": "131001" },
  { "lat": 28.5382, "lng": 77.215, "area": "Lajpat Nagar", "pincode": "110024" },
  { "lat": 28.5244, "lng": 77.2066, "area": "Greater Kailash", "pincode": "110048" },
  { "lat": 28.4089, "lng": 77.3178, "area": "Faridabad Sector 10", "pincode": "121010" },
  { "lat": 28.76, "lng": 77.25, "area": "Burari", "pincode": "110084" },
  { "lat": 28.4089, "lng": 77.3178, "area": "Faridabad Sector 3", "pincode": "121003" },
  { "lat": 28.735, "lng": 77.098, "area": "Bawana", "pincode": "110039" },
  { "lat": 28.645, "lng": 77.209, "area": "Paharganj", "pincode": "110055" },
  { "lat": 28.423, "lng": 77.031, "area": "Sohna", "pincode": "122104" },
  { "lat": 28.6825, "lng": 77.178, "area": "Wazirpur", "pincode": "110052" },
  { "lat": 28.474, "lng": 77.04, "area": "Badshahpur", "pincode": "122101" },
  { "lat": 28.6351, "lng": 77.2337, "area": "Daryaganj", "pincode": "110002" },
  { "lat": 28.38, "lng": 77.42, "area": "Palwal", "pincode": "121102" },
  { "lat": 28.682, "lng": 77.219, "area": "Civil Lines", "pincode": "110054" },
  { "lat": 28.4595, "lng": 77.0266, "area": "Gurgaon Sector 4", "pincode": "122004" },
  { "lat": 28.6721, "lng": 77.2663, "area": "Gandhi Nagar", "pincode": "110031" },
  { "lat": 29.3909, "lng": 76.9635, "area": "Panipat", "pincode": "132103" },
  { "lat": 28.608, "lng": 77.213, "area": "South Block", "pincode": "110011" },
  { "lat": 28.628, "lng": 77.239, "area": "Gole Market", "pincode": "110004" },
  { "lat": 28.5562, "lng": 77.1, "area": "IGI Airport", "pincode": "110037" }
]}, status=200)


class ContentInsightsDataView(APIView):
    def get(self, request, brand_id: int):
        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            return Response({"error": f"Brand with id {brand_id} not found"}, status=404)
        return Response(serve_brand_template_json(brand, JsonTemplate.CONTENT_INSIGHTS.slug), status=200)

class GenerateContentView(APIView):

    def post(self, request):
        product_id = request.data.get("product_id")
        section = request.data.get("section")
        brand_id = request.data.get("brand_id")

        if not product_id or not section or not brand_id:
            raise APIException("product_id, brand_id and section required")

        # ---------- LOAD PRODUCT ----------
        brand = Brand.objects.get(id=brand_id)
        catalog = serve_brand_template_json(brand, JsonTemplate.CATALOG.slug)
        brand_data = catalog.get(brand.name, [])

        product = next(
            (p for p in brand_data if str(p.get("id")) == str(product_id)),
            None
        )

        if not product:
            raise NotFound("Product not found")

        # ---------- EXTRACT PRODUCT DATA ----------
        title = product.get("product_title", "N/A")
        brand_name = product.get("brand", brand.name)
        detail_data = product.get("detail_data", {})

        description = detail_data.get("description", "No description available.")
        bullets = "\n".join(detail_data.get("bullets", [])) or "No features available."

        # ---------- FETCH KEYWORDS ----------
        keywords = CategoryKeyword.objects.filter(
            platform__iexact=product.get("data_source")
        ).values_list("keyword", flat=True)

        keywords_text = ", ".join(keywords)

        # ---------- BUILD ADVANCED PROMPT ----------
        prompt = f"""
You are an expert E-commerce Copywriter and Senior Brand Manager.

### INPUT DATA (DO NOT HALLUCINATE)
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

### SCORING RULES
"""

        if section == "features":
            prompt += """
Generate 5-6 bullet features:

- Total words: 100–300
- Each bullet starts with **Feature Name:**
- Professional tone
- Keywords integrated naturally
"""
        else:
            prompt += """
Generate description:

- 100–300 words
- No bullet points
- British English tone
- Professional yet engaging
"""

        prompt += """
### PROCESS
1. Analyze facts
2. Draft content
3. Review accuracy
4. Refine final version

### OUTPUT
Return ONLY final content.
"""

        # ---------- CALL LLM ----------
        results = LLMService.generate_content(prompt)

        return Response(results)
    

class UpdateProductContentView(APIView):

    def post(self, request):
        product_id = request.data.get("product_id")
        brand_id = request.data.get("brand_id")
        section = request.data.get("section")
        content = request.data.get("content")
        brand = Brand.objects.get(id=brand_id)
        catalog = serve_brand_template_json(brand, JsonTemplate.CATALOG.slug)
        brand_data = catalog.get(brand.name, [])
        product = next((p for p in brand_data if str(p.get("id")) == str(product_id)), None)
        if not product:
            raise NotFound("Product not found")

        # Update JSON content
        if section == "features":
            product["detail_data"]["bullets"] = content.split("\n")
        else:
            product["detail_data"]["description"] = content

        # Save back JSON file
        bj = BrandJsonFile.objects.get(brand=brand, template=JsonTemplate.CATALOG.slug)
        full_path = os.path.join(settings.MEDIA_ROOT, bj.file_path)
        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=4)

        return Response({"success": True})