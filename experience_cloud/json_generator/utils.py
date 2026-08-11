import ast
import json
import logging
import os
import re
import shutil
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.exceptions import APIException, NotFound

from experience_cloud.catalog.models import Platform
from experience_cloud.json_generator.exceptions import FileWriteException
from experience_cloud.json_generator.models import RegionJsonFile

logger = logging.getLogger(__name__)

def archive_old_json_file(old_relative_path, brand_name, region_name):
    """Relocate an existing JSON payload file into a timestamped archival directory structure.

    Format: media/archive/brands/<brand>/<region>/<YYYY-MM-DD>/<filename>.
    """
    if not old_relative_path:
        return

    try:
        from django.conf import settings
        full_old_path = os.path.join(settings.MEDIA_ROOT, old_relative_path)
        if not os.path.exists(full_old_path):
            return

        brand_slug = slugify(brand_name)
        region_slug = slugify(region_name)
        date_folder = datetime.now().strftime('%Y-%m-%d')

        filename = os.path.basename(full_old_path)
        base_name, ext = os.path.splitext(filename)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        archived_filename = f"{base_name}-{timestamp}{ext}"

        archive_folder = os.path.join(settings.MEDIA_ROOT, 'archive', 'brands', brand_slug, region_slug, date_folder)
        os.makedirs(archive_folder, exist_ok=True)

        archive_path = os.path.join(archive_folder, archived_filename)
        shutil.move(full_old_path, archive_path)
        logger.info(f"Archived old JSON file -> {archive_path}")
    except OSError as e:
        logger.error(f"Failed to archive old JSON file {old_relative_path}: {e}")

def save_region_template(
    data, brand_name, template, region_name="unknown",
    existing_path=None, file_name_override=None,
    parent_folder_override=None, file_format=None
):
    """Serialize and save data to the filesystem, using JsonTemplate configurations."""
    ctx = f"[Data Gen | Brand: {brand_name} | Template: {template}]"
    logger.info(f"{ctx} Attempting to save file...")

    try:
        if existing_path:
            archive_old_json_file(existing_path, brand_name, region_name)

        from experience_cloud.json_generator.models import JsonTemplate
        template_obj = JsonTemplate.objects.filter(template=template).first()

        if not file_name_override and template_obj and template_obj.file_name:
            file_name_override = template_obj.file_name
        if not parent_folder_override and template_obj and template_obj.parent_folder:
            parent_folder_override = template_obj.parent_folder
        if not file_format:
            file_format = template_obj.file_format if template_obj and template_obj.file_format else 'json'

        brand_slug = slugify(brand_name)
        region_slug = slugify(region_name)

        if file_name_override:
            filename = file_name_override
            if not filename.endswith(f'.{file_format}'):
                filename = f"{filename}.{file_format}"
        else:
            template_slug = slugify(template)
            filename = f"{template_slug}.{file_format}"

        folder_parts = ['brands', brand_slug, region_slug]
        if parent_folder_override:
            folder_parts.append(parent_folder_override)

        folder = os.path.join(settings.MEDIA_ROOT, *folder_parts)
        os.makedirs(folder, exist_ok=True)
        filepath = os.path.join(folder, filename)
        relative_path = "/".join([*folder_parts, filename])

        encoding_format = 'utf-8-sig' if file_format == 'csv' else 'utf-8'
        with open(filepath, 'w', encoding=encoding_format, newline='') as f:
            if file_format == 'csv':
                import csv
                if isinstance(data, list) and len(data) > 0:
                    if isinstance(data[0], dict):
                        writer = csv.DictWriter(f, fieldnames=data[0].keys())
                        writer.writeheader()
                        writer.writerows(data)
                    elif isinstance(data[0], (list, tuple)):
                        writer = csv.writer(f)
                        writer.writerows(data)
                    else:
                        f.write(str(data))
                else:
                    f.write(str(data))
            elif file_format in ['html', 'txt', 'xml']:
                f.write(data if isinstance(data, str) else str(data))
            else:
                json.dump(data, f, ensure_ascii=False, indent=4, cls=DjangoJSONEncoder)

        logger.info(f"{ctx} Saved file -> {filepath}")
        return filename, relative_path
    except Exception as exc:
        logger.exception(f"{ctx} File save failed")
        raise FileWriteException(
            message="File save failed",
            extra=str(exc)
        ) from exc


def match_brand(product_brand, input_brand):
    """Perform a rigorous boundary-matched regex search to verify if a product brand matches a given input string."""
    if not product_brand or not input_brand:
        return None
    pb = product_brand.strip().lower()
    ib = input_brand.strip().lower()
    return product_brand if re.search(rf"\b{re.escape(pb)}\b", ib) else None

def match_brands(brands, input_brand):
    """Perform a rigorous boundary-matched regex search to verify if an input brand matches any brand aliases."""
    if not brands or not input_brand:
        return None
    ib = input_brand.strip().lower()
    ib_no_hyphen = ib.replace('-', '')

    if isinstance(brands, dict):
        for brand, aliases in brands.items():
            if not brand:
                continue
            names_to_check = [brand] + (aliases if aliases else [])
            for name in names_to_check:
                if not name:
                    continue
                pb = name.strip().lower()
                if re.search(rf"\b{re.escape(pb)}\b", ib):
                    return brand
                pb_no_hyphen = pb.replace('-', '')
                if pb_no_hyphen and re.search(rf"\b{re.escape(pb_no_hyphen)}\b", ib_no_hyphen):
                    return brand
    else:
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

def get_platform_group_map():
    """Extract and aggregate all active Platform codes mapped dynamically by their core platform_type classification."""
    map_data = defaultdict(list)
    for p in Platform.objects.filter(status='active'):
        map_data[p.platform_type].append(p.code)
    return dict(map_data)

def get_platform_list(platform_types: list):
    """Retrieve an aggregated, deduplicated set of active platform codes for the requested platform types."""
    result = set()
    group_map = get_platform_group_map()
    for p_type in platform_types:
        platforms = group_map.get(p_type)
        if not platforms:
            continue
        result.update(platforms)
    return list(result)

def parse_metric(val: Any, default: int = 0) -> int:
    """Sanitize and cast unstructured string or float metric representations into strict integers."""
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
    except (ValueError, TypeError):
        pass
    return default

def parse_float(val: Any, default: float = 0.0) -> float:
    """Sanitize and cast unstructured strings or fractions into clean floating-point representations."""
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
    except (ValueError, TypeError):
        pass
    return default

def parse_price(val: Any, default: float | None = None) -> float | None:
    """Sanitize and safely cast raw pricing strings (stripping currency symbols and commas) into strict float values."""
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
    except (ValueError, TypeError):
        return default

def parse_array(val: Any) -> list[str]:
    """Safely parse and flatten comma-separated strings or JSON arrays into strict Python lists of strings."""
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
    except (ValueError, TypeError, SyntaxError):
        return []
    return []

def to_list(val: Any) -> list[str]:
    """Dynamically cast unstructured tuples, newline-delimited strings, or JSON arrays into flattened string lists."""
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
    except (ValueError, TypeError):
        pass
    return []

def split_path(value: Any) -> list[str]:
    """Break down delimited breadcrumb trails or taxonomy string paths into normalized hierarchical list segments."""
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    text = str(value).strip()
    parts = re.split(r'[>,|/\n,]+', text)
    return [p.strip() for p in parts if p.strip()]

def normalize_availability(value: Any, default: str | None = "Unavailable") -> str | None:
    """Cross-reference availability text against known stock indicators to return 'Available' or 'Unavailable'."""
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


class ItemGenerator:
    """A persistent generator wrapper that caches database-yielded products into local JSON Lines (.jsonl) files.

    This architecture allows memory-efficient, multi-pass iteration without triggering repeated database loads.
    """
    def __init__(self, func: Callable, *args: Any, **kwargs: Any):
        """Initialize the ItemGenerator."""
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._is_cached = False
        self._cache_file = None
        self.total_count = 0

    def __iter__(self):
        """Iterate over the generator, caching items if necessary."""
        import json
        import os

        from django.core.serializers.json import DjangoJSONEncoder

        from experience_cloud.json_generator.schemas import ProductSchema

        if not self._is_cached:
            import tempfile
            fd, self._cache_file = tempfile.mkstemp(suffix='.jsonl', prefix='agy_item_cache_')
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                for item in self.func(*self.args, **self.kwargs):
                    f.write(json.dumps(item.__dict__, cls=DjangoJSONEncoder) + '\n')
                    self.total_count += 1
                    yield item
            self._is_cached = True
            logger.info(f"ItemGenerator built local cache -> {self._cache_file}")
        else:
            if self._cache_file and os.path.exists(self._cache_file):
                with open(self._cache_file, encoding='utf-8') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        data = json.loads(line)
                        item = ProductSchema()
                        for k, v in data.items():
                            if k == 'scraped_date' and isinstance(v, str):
                                try:
                                    from django.utils.dateparse import parse_date, parse_datetime
                                    parsed = parse_datetime(v)
                                    if parsed is None:
                                        parsed = parse_date(v)
                                    if parsed is not None:
                                        v = parsed
                                except (ValueError, TypeError):
                                    pass
                            setattr(item, k, v)
                        yield item

    def cleanup(self):
        """Remove the cached JSONL file if it exists."""
        import os
        if self._cache_file and os.path.exists(self._cache_file):
            try:
                os.remove(self._cache_file)
                logger.info(f"ItemGenerator cleaned up cache -> {self._cache_file}")
            except OSError as e:
                logger.error(f"Failed to cleanup ItemGenerator cache {self._cache_file}: {e}")

def safe_float(value, default=0.0):
    """Sanitize strict non-available indicators ('NA', '--') and gracefully cast valid numerical strings into floats."""
    try:
        if value in [None, "", "--", "NA", "N/A"]:
            return default
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return default

def load_json_response(file_path):
    """Read, deserialize, and return a structural JSON dictionary from the filesystem."""
    try:
        with open(file_path, encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError as e:
        raise NotFound(detail=f"File not found: {file_path}") from e
    except UnicodeDecodeError as e:
        raise APIException(detail=f"Encoding error: {e!s}") from e
    except json.JSONDecodeError as e:
        raise APIException(detail=f"JSON error: {e!s}") from e

def serve_region_template(region_id: int, template_name: str):
    """Query RegionJsonFile records and securely serve the underlying raw JSON payload file from the filesystem."""
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
        raise NotFound(detail=f"Database error querying region {region_id} and template {template_name}") from e

    if not rj.file_path:
        raise NotFound(detail=f"Data not available for region {region_id} and template {template_name}")

    full_path = os.path.join(settings.MEDIA_ROOT, rj.file_path)
    if not os.path.exists(full_path):
        raise NotFound(detail=f"Data not available for region {region_id} and template {template_name}")

    return load_json_response(full_path)

def save_or_update_region_json(
    region_id: int, template_name: str, json_data: dict | list, brand_name: str, task=None, products_processed: int = 0
):
    """Serialize a JSON payload, atomically archive the old payload, and update RegionJsonFile metrics.

    Often consumed natively by advanced template builders orchestrating multi-file generation cycles.
    """
    from core.organizations.models import Region
    from experience_cloud.json_generator.models import JsonTemplate, RegionJsonFile
    region_name = "unknown"
    if region_id:
        region = Region.objects.filter(id=region_id).first()
        if region:
            region_name = region.name

        # Archive existing file if it exists
        existing_file = RegionJsonFile.objects.filter(region_id=region_id, template__template=template_name).first()
        if existing_file and existing_file.file_path:
            archive_old_json_file(existing_file.file_path, brand_name, region_name)

    template_obj = JsonTemplate.objects.filter(template=template_name).first()
    file_name_override = template_obj.file_name if template_obj and template_obj.file_name else None
    parent_folder_override = template_obj.parent_folder if template_obj and template_obj.parent_folder else None

    file_name, file_path = save_region_template(
        json_data, brand_name, template_name, region_name,
        file_name_override=file_name_override,
        parent_folder_override=parent_folder_override
    )

    import os

    from django.conf import settings

    full_path = os.path.join(settings.MEDIA_ROOT, file_path)
    file_size = os.path.getsize(full_path) if os.path.exists(full_path) else 0

    update_kwargs = {
        "file_name": file_name,
        "file_path": file_path,
        "file_size": file_size,
        "checksum": "calculated",
        "products_processed": products_processed,
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


def safe_parse_llm_json(content: str) -> dict:
    """Attempt to parse LLM JSON output robustly."""
    import json
    import logging
    logger = logging.getLogger(__name__)
    try:
        if content.startswith("```json"):
            content = content.strip("`").replace("json\n", "", 1)
        start = content.find("{")
        end = content.rfind("}")
        json_str = content[start:end + 1] if start != -1 and end != -1 else content

        try:
            import json_repair
            return json_repair.loads(json_str)
        except ImportError:
            return json.loads(json_str)
    except ValueError as e:
        logger.error(f"Failed to parse LLM JSON: {e}\nContent: {content}")
        return {}
