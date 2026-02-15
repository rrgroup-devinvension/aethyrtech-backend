from django.utils import timezone
from django.conf import settings
from pathlib import Path
import json
import logging
import time
from django.db import transaction
from apps.scheduler.data_dump.quickcommerce_client import QuickCommerceClient
from apps.scheduler.data_dump.utils import normalize_reviews, normalize_rating, normalize_price, split_images
from apps.scheduler.models import QuickCommerceSearch, QuickCommerceProduct, QuickCommerceProductDetail
from apps.scheduler.enums import QuickCommercePlatforms
from apps.scheduler.exceptions import SchedulerBaseException, DataProcessingException, ExternalAPIException
logger = logging.getLogger(__name__)
from apps.scheduler.utility.datadump_api_logger import log_success as dd_log_success, log_error as dd_log_error

def perform_data_dump(task):
    logger.info(f"DATA_DUMP STARTED | Task={task.id}")
    keyword = task.extra_context.get("keyword")
    pincode = task.extra_context.get("pincode")
    platforms = task.extra_context.get("platforms")
    failures = []
    failures = []

    print("Received Task → Keyword: {}, Pincode: {}, Platforms: {}".format(keyword, pincode, platforms))

    for platform in QuickCommercePlatforms:
        try:
            platform_name = platform.value
            if platform_name not in platforms:
                dd_log_success(pincode=pincode, keywords=[keyword], response={"platform": platform.value, "status": "skipped"})
                continue
            response = QuickCommerceClient.fetch_results(
                keyword=keyword,
                pincode=pincode,
                platform=platform.value
            )
            # Log datadump success for this platform
            dd_log_success(pincode=pincode, keywords=[keyword], response={"platform": platform.value, "status": "results_present"})
            file_path, file_size = save_api_response_to_file(
                task=task,
                response=response,
                keyword=keyword,
                pincode=pincode,
                platform=platform.value
            )
            search_obj = save_search_meta(
                task=task,
                response=response,
                keyword=keyword,
                pincode=pincode,
                platform=platform.value,
                file_path=file_path,
                file_size=file_size
            )
            save_products(search_obj, response)
        except SchedulerBaseException as exc:
            failures.append({
                "platform": platform.value,
                "code": exc.error_code,
                "message": exc.user_message,
            })
        except Exception as exc:
            failures.append({
                "platform": platform.value,
                "code": "SYSTEM_ERROR",
                "message": str(exc)
            })

    if failures:
        combined_message = ", ".join([
            f"{f['platform']}: {f['message']}"
            for f in failures
        ])
        logger.error("DATA_DUMP FAILURES \t\t error: %s", combined_message)
        dd_log_error(pincode=pincode, keywords=[keyword], error=combined_message, extra={"failures": failures})
        raise DataProcessingException(
            message=combined_message,
            extra=failures
        )

    dd_log_success(pincode=pincode, keywords=[keyword], response={'status': 'completed'})
    logger.info(f"DATA_DUMP COMPLETED | Task={task.id}")

def save_search_meta(task, response, keyword, pincode, platform, file_path, file_size):
    log = response.get("request_log", {})
    return QuickCommerceSearch.objects.create(
        task_id=task.id,
        keyword=keyword,
        pincode=pincode,
        platform=platform,
        request_time = timezone.now(),
        response_time = timezone.now(),
        process_time=log.get("request_process_time", 0),
        status_code=log.get("statusCode"),
        status="SUCCESS" if log.get("statusCode") == 200 else "FAILED",
        response_file=file_path,
        response_file_size=file_size
    )

@transaction.atomic
def save_products(search_obj, response):

    results = response.get("results", [])
    if not results:
        logger.warning("No products returned from API")
        return

    platform = search_obj.platform
    keyword = search_obj.keyword
    pincode = search_obj.pincode
    incoming_map = {}
    incoming_ids = set()

    for item in results:
        product_uid = str(item.get("id", "")).strip()
        if not product_uid:
            continue
        incoming_ids.add(product_uid)
        incoming_map[product_uid] = item

    # ✅ Fetch EXISTING products by BUSINESS KEY
    existing_products = QuickCommerceProduct.objects.filter(
        keyword=keyword,
        pincode=pincode,
        platform=platform,
        product_uid__in=incoming_ids
    )

    existing_map = {
        p.product_uid: p
        for p in existing_products
    }

    to_create = []
    to_update = []

    for product_uid, item in incoming_map.items():
        detail = item.get("detail_data", {})
        defaults = {
            "search": search_obj,  # latest batch link
            "rank": item.get("rank"),
            "title": item.get("product_title"),
            "brand": item.get("brand"),
            "category": item.get("category"),
            "availability": item.get("availability"),
            "msrp": item.get("msrp"),
            "sell_price": detail.get("sell_price"),
            "rating": detail.get("rating"),
            "reviews": detail.get("reviews"),
            "product_url": item.get("Platform url of the SKU"),
            "thumbnail": item.get("thumbnail_image_url"),
            "main_image": item.get("main_image"),
            "detail_page_images": item.get("detail_page_images"),
            "platform": platform,
            "keyword": keyword,
            "pincode": pincode,
        }

        if product_uid in existing_map:
            product = existing_map[product_uid]
            for field, value in defaults.items():
                setattr(product, field, value)
            to_update.append(product)
        else:
            to_create.append(
                QuickCommerceProduct(
                    product_uid=product_uid,
                    **defaults
                )
            )

    if to_create:
        QuickCommerceProduct.objects.bulk_create(
            to_create,
            batch_size=500,
            ignore_conflicts=True  # safety net
        )

    if to_update:
        QuickCommerceProduct.objects.bulk_update(
            to_update,
            fields=[
                "search",
                "rank", "title", "brand", "category",
                "availability", "msrp", "sell_price",
                "rating", "reviews", "product_url",
                "thumbnail", "main_image",
                "detail_page_images",
                "platform", "keyword", "pincode"
            ],
            batch_size=500
        )

    QuickCommerceProduct.objects.filter(
        keyword=keyword,
        pincode=pincode,
        platform=platform
    ).exclude(
        product_uid__in=incoming_ids
    ).delete()

    # ✅ Sync details
    _sync_product_details(search_obj, incoming_map)
    logger.info(
        f"Products Sync Done | "
        f"Created={len(to_create)} "
        f"Updated={len(to_update)} "
    )
    dd_log_success(pincode=pincode, keywords=[keyword], response={'created': len(to_create), 'updated': len(to_update)})

def _sync_product_details(search_obj, incoming_map):

    keyword = search_obj.keyword
    pincode = search_obj.pincode
    platform = search_obj.platform
    product_uids = incoming_map.keys()
    # ✅ Fetch correct products by business key
    products = list(
        QuickCommerceProduct.objects.filter(
            product_uid__in=product_uids,
            keyword=keyword,
            pincode=pincode,
            platform=platform
        )
    )
    product_map = {
        p.product_uid: p
        for p in products
    }
    # Existing details
    existing_details = QuickCommerceProductDetail.objects.filter(
        product__in=products
    )
    detail_map = {
        d.product_id: d
        for d in existing_details
    }

    to_create = []
    to_update = []

    for product_uid, item in incoming_map.items():
        product = product_map.get(product_uid)
        if not product:
            continue
        detail = item.get("detail_data", {})
        defaults = {
            "model": detail.get("model"),
            "sold_by": detail.get("sold_by"),
            "shipped_by": detail.get("shipped_by"),
            "description": detail.get("description"),
            "bullets": detail.get("bullets", []),
            "image_count": detail.get("images", 0),
            "video_count": detail.get("videos", 0),
        }
        existing = detail_map.get(product.id)
        if existing:
            for field, value in defaults.items():
                setattr(existing, field, value)
            to_update.append(existing)
        else:
            to_create.append(
                QuickCommerceProductDetail(
                    product=product,
                    **defaults
                )
            )

    if to_create:
        QuickCommerceProductDetail.objects.bulk_create(
            to_create,
            batch_size=500
        )

    if to_update:
        QuickCommerceProductDetail.objects.bulk_update(
            to_update,
            fields=[
                "model",
                "sold_by",
                "shipped_by",
                "description",
                "bullets",
                "image_count",
                "video_count"
            ],
            batch_size=500
        )

def save_api_response_to_file(task, response, keyword, pincode, platform):

    base_dir = (
        Path(settings.MEDIA_ROOT)
        / "quickcommerce"
        / timezone.now().strftime("%Y")
        / timezone.now().strftime("%m")
        / keyword.replace(" ", "_")
        / pincode.replace(" ", "_")
        / platform.replace(" ", "_")
    )
    base_dir.mkdir(parents=True, exist_ok=True)
    keyword = task.extra_context.get("keyword", "unknown").replace(" ", "_")
    pincode = task.extra_context.get("pincode", "unknown")
    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{keyword}_{pincode}_{timestamp}.json"
    filepath = base_dir / filename
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(response, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.exception(f"Failed to write API response file: {filepath}")
        dd_log_error(pincode=pincode, keywords=[keyword], error=str(exc), extra={'filepath': str(filepath)})

    file_size = filepath.stat().st_size
    relative_path = filepath.relative_to(settings.MEDIA_ROOT)
    if not task.extra_context:
        task.extra_context = {}
    task.extra_context.setdefault("files", [])
    task.extra_context["files"].append({
        "platform": platform,
        "filename": filename,
        "path": str(relative_path),
        "size": file_size
    })
    # task.save(update_fields=["extra_context"])
    logger.info(f"Saved JSON → {filepath}")
    return str(relative_path), file_size
