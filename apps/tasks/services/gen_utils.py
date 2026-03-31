import json
import os
from django.conf import settings
from django.conf import settings
from apps.scheduler.models import BrandJsonFile
import os, json
from rest_framework.exceptions import NotFound, APIException
from apps.scheduler.json_builder.utils import save_json_to_file
from django.utils import timezone

def safe_float(value, default=0.0):
    try:
        if value in [None, "", "--", "NA", "N/A"]:
            return default
        return float(str(value).replace(",", "").strip())
    except:
        return default
    
def save_or_update_brand_json(brand, template_name, json_data):
    try:
        # 1️⃣ Save file first
        filename, relative_path = save_json_to_file(
            json_data,
            brand.name,
            template_name
        )

        # 2️⃣ Update or Create DB entry
        obj, created = BrandJsonFile.objects.update_or_create(
            brand=brand,
            template=template_name,
            defaults={
                "filename": filename,
                "file_path": relative_path,
                "last_run_time": timezone.now(),
                "last_completed_time": timezone.now(),
                "last_run_status": "SUCCESS",
                "last_synced": timezone.now(),
                "error_message": None
            }
        )

        return obj

    except Exception as exc:
        raise Exception(f"Failed to save/update BrandJsonFile: {str(exc)}")
    
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

