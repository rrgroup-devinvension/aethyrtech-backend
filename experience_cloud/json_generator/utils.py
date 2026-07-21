from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
import os
import json
import logging
from contextlib import contextmanager
from experience_cloud.json_generator.exceptions import FileWriteException, DatabaseException
import re

logger = logging.getLogger(__name__)

def save_json_to_file(json_data, brand_name, template):
    try:
        media_sub = getattr(settings, 'SCHEDULER_JSON_MEDIA_SUBPATH', 'jsons')
        brand_slug = slugify(brand_name)
        folder = os.path.join(settings.MEDIA_ROOT, media_sub, brand_slug)
        os.makedirs(folder, exist_ok=True)
        filename = f"{template}-{timezone.now().strftime('%Y%m%d%H%M%S')}.json"
        filepath = os.path.join(folder, filename)
        relative_path = f"{media_sub}/{brand_slug}/{filename}"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"Saved JSON file ? {filepath}")
        return filename, relative_path
    except Exception as exc:
        logger.exception("JSON file save failed")
        raise FileWriteException(
            message="JSON file save failed",
            extra=str(exc)
        )


def match_brand(product_brand, input_brand):
    if not product_brand or not input_brand:
        return None
    pb = product_brand.strip().lower()
    ib = input_brand.strip().lower()
    return product_brand if re.search(rf"\b{re.escape(pb)}\b", ib) else None

def match_brands(brands, input_brand):
    if not brands or not input_brand:
        return None
    ib = input_brand.strip().lower()
    ib_no_hyphen = ib.replace('-', '')    
    for brand in brands:
        if not brand:
            continue
        pb = brand.strip().lower()
        if re.search(rf"\b{re.escape(pb)}\b", ib):
            return brand
        pb_no_hyphen = pb.replace('-', '')
        if pb_no_hyphen and re.search(rf"\b{re.escape(pb_no_hyphen)}\b", ib_no_hyphen):
            return brand
    return None

from collections import defaultdict
from experience_cloud.catalog.models import Platform

def get_platform_group_map():
    map_data = defaultdict(list)
    for p in Platform.objects.filter(status='active'):
        map_data[p.platform_type].append(p.value)
    return dict(map_data)

def get_platform_list(platform_types: list):
    result = set()
    group_map = get_platform_group_map()
    for p_type in platform_types:
        platforms = group_map.get(p_type)
        if not platforms:
            continue
        result.update(platforms)
    return list(result)

import ast
from typing import List, Optional, Any
from decimal import Decimal

def parse_metric(val: Any, default: int = 0) -> int:
    if val is None:
        return default
    try:
        if isinstance(val, int):
            return val
        if isinstance(val, float):
            return int(val)
        if isinstance(val, str):
            s = val.strip().lower()
            if not s:
                return default
            s = s.replace("+", "").replace(",", "")
            multiplier = 1
            if "k" in s:
                multiplier = 1000
                s = s.replace("k", "")
            elif "m" in s:
                multiplier = 1000000
                s = s.replace("m", "")
            match = re.search(r"\d+(\.\d+)?", s)
            if match:
                number = float(match.group())
                return int(number * multiplier)
    except Exception:
        pass
    return default

def parse_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        if isinstance(val, (int, float, Decimal)):
            return float(val)
        if isinstance(val, str):
            s = val.strip()
            if not s:
                return default
            if "/" in s:
                s = s.split("/")[0]
            s = s.replace(",", ".")
            match = re.search(r"\d+(\.\d+)?", s)
            if match:
                return float(match.group())
    except Exception:
        pass
    return default

def parse_price(val: Any, default: Optional[float] = None) -> Optional[float]:
    if val is None:
        return default
    try:
        if isinstance(val, (int, float)):
            return float(val)
        s = str(val).strip()
        if not s:
            return default
        s = s.replace('Rs.', '').replace('₹', '').replace('$', '').replace(',', '')
        s = re.sub(r'[^0-9\.\-]', '', s)
        return float(s) if s else default
    except Exception:
        return default

def parse_array(val: Any) -> List[str]:
    if not val:
        return []
    try:
        if isinstance(val, (list, tuple)):
            return list(val)
        if isinstance(val, str):
            s = val.strip()
            if s.startswith("[") and "'" in s:
                return ast.literal_eval(s)
            if s.startswith("["):
                return json.loads(s)
            return [x.strip() for x in s.split(",") if x.strip()]
    except Exception:
        return []
    return []

def to_list(val: Any) -> List[str]:
    if not val:
        return []
    try:
        if isinstance(val, (list, tuple)):
            return [str(x).strip() for x in val if str(x).strip()]
        if isinstance(val, str):
            s = val.strip()
            if s.startswith('[') and s.endswith(']'):
                data = json.loads(s)
                return [str(x).strip() for x in data if str(x).strip()]
            if '\n' in s:
                return [x.strip() for x in s.splitlines() if x.strip()]
            return [x.strip() for x in s.split(',') if x.strip()]
    except Exception:
        pass
    return []

def split_path(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    text = str(value).strip()
    parts = re.split(r'[>,|/\n,]+', text)
    return [p.strip() for p in parts if p.strip()]

def normalize_availability(value: Any, default: Optional[str] = "Unavailable") -> Optional[str]:
    if not value:
        return default
    text = str(value).strip().lower()
    available_keywords = ["in stock", "available", "yes", "true", "1", "instock", "stock available"]
    unavailable_keywords = ["out of stock", "unavailable", "no", "false", "0", "sold out"]
    if any(k in text for k in available_keywords):
        return "Available"
    if any(k in text for k in unavailable_keywords):
        return "Unavailable"
    return default


from typing import Any, Callable

class ItemGenerator:
    """A wrapper for a generator function and its args so it can be iterated multiple times."""
    def __init__(self, func: Callable, *args: Any, **kwargs: Any):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __iter__(self):
        return self.func(*self.args, **self.kwargs)

from experience_cloud.json_generator.models import RegionJsonFile
from rest_framework.exceptions import NotFound, APIException

def safe_float(value, default=0.0):
    try:
        if value in [None, "", "--", "NA", "N/A"]:
            return default
        return float(str(value).replace(",", "").strip())
    except:
        return default

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

def serve_region_template_json(region_id: int, template_name: str):
    try:
        rj = RegionJsonFile.objects.filter(
            region_id=region_id, 
            template__template=template_name
        ).order_by('-id').first()
        
        if not rj:
            raise NotFound(detail=f"Data not available for region {region_id} and template {template_name}")
            
    except Exception as e:
        if isinstance(e, NotFound):
            raise
        raise NotFound(detail=f"Database error querying region {region_id} and template {template_name}")

    if not rj.file_path:
        raise NotFound(detail=f"Data not available for region {region_id} and template {template_name}")

    full_path = os.path.join(settings.MEDIA_ROOT, rj.file_path)
    if not os.path.exists(full_path):
        raise NotFound(detail=f"Data not available for region {region_id} and template {template_name}")
    
    return load_json_response(full_path)

def save_or_update_region_json(region_id: int, template_name: str, json_data: dict, brand_name: str, task=None):
    """
    Saves a JSON file and updates the corresponding RegionJsonFile record.
    Used internally by complex builders that need to handle their own saving logic.
    """
    file_name, file_path = save_json_to_file(json_data, brand_name, template_name)
    
    import os
    from django.conf import settings
    
    full_path = os.path.join(settings.MEDIA_ROOT, file_path)
    file_size = os.path.getsize(full_path) if os.path.exists(full_path) else 0
    
    update_kwargs = {
        "file_name": file_name,
        "file_path": file_path,
        "file_size": file_size,
        "checksum": "calculated",
        "status": 'SUCCESS',
        "last_generated_at": timezone.now()
    }
    
    if task and task.metadata and 'file_id' in task.metadata:
        RegionJsonFile.objects.filter(id=task.metadata['file_id']).update(**update_kwargs)
    else:
        # Fallback if no task is provided, update latest
        RegionJsonFile.objects.filter(
            region_id=region_id, 
            template__template=template_name
        ).update(**update_kwargs)
        
    return file_name, file_path
