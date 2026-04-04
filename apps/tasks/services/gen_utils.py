import json
import os
from django.conf import settings
from django.conf import settings
from apps.scheduler.models import BrandJsonFile
import os, json
from rest_framework.exceptions import NotFound, APIException
from apps.scheduler.json_builder.utils import save_json_to_file
from django.utils import timezone
from django.utils.text import slugify

def safe_float(value, default=0.0):
    try:
        if value in [None, "", "--", "NA", "N/A"]:
            return default
        return float(str(value).replace(",", "").strip())
    except:
        return default
    
def save_or_update_brand_json(brand, template_name, json_data, extra_files=None):
    try:
        # Save JSON file
        filename, relative_path = save_json_to_file(
            json_data,
            brand.name,
            template_name
        )

        # Extract folder + timestamp from JSON filename
        # filename example: template-20250610123045.json
        base_name = filename.replace(".json", "")
        timestamp = base_name.split("-")[-1]

        # Absolute folder path
        media_sub = getattr(settings, 'SCHEDULER_JSON_MEDIA_SUBPATH', 'jsons')
        brand_slug = slugify(brand.name)
        folder = os.path.join(settings.MEDIA_ROOT, media_sub, brand_slug)

        # Save extra files in SAME folder with SAME timestamp
        if extra_files:
            import csv

            for file in extra_files:
                file_ext = file["type"]
                file_name = file["name"].replace(f".{file_ext}", "")

                # NEW filename with SAME timestamp
                final_filename = f"{file_name}-{timestamp}.{file_ext}"
                path = os.path.join(folder, final_filename)

                if file_ext == "csv":
                    with open(path, "w", newline='', encoding="utf-8-sig") as f:
                        writer = csv.writer(f)

                        # Only write header if exists
                        if file.get("header"):
                            writer.writerow(file["header"])

                        writer.writerows(file.get("rows", []))

                elif file_ext == "html":
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(file.get("content", ""))

        # DB Update
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

