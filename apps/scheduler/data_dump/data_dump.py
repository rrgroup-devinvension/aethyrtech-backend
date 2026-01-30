from django.utils import timezone
from django.conf import settings
from pathlib import Path
import json
import logging
from django.db import transaction
from apps.scheduler.data_dump.quickcommerce_client import QuickCommerceClient
from apps.scheduler.data_dump.utils import normalize_reviews, normalize_rating, normalize_price, split_images
from apps.scheduler.models import QuickCommerceSearch, QuickCommerceProduct, QuickCommerceProductDetail
from apps.scheduler.enums import QuickCommercePlatforms
from apps.scheduler.exceptions import SchedulerBaseException, DataProcessingException
logger = logging.getLogger(__name__)

def perform_data_dump(task):
    logger.info(f"DATA_DUMP STARTED | Task={task.id}")
    keyword = task.extra_context.get("keyword")
    pincode = task.extra_context.get("pincode")
    platforms = task.extra_context.get("platforms")
    failures = []
    failures = []

    for platform in QuickCommercePlatforms:
        try:
            if platform not in platforms:
                continue
            response = QuickCommerceClient.fetch_results(
                keyword=keyword,
                pincode=pincode,
                platform=platform.value
            )
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
        raise DataProcessingException(
            message=combined_message,
            extra=failures
        )

    logger.info(f"DATA_DUMP COMPLETED | Task={task.id}")

def save_search_meta(task, response, keyword, pincode, platform, file_path, file_size):
    log = response.get("request_log", {})
    return QuickCommerceSearch.objects.create(
        task_id=task.id,
        keyword=keyword,
        pincode=pincode,
        platform=platform,
        request_time=log.get("request_time"),
        response_time=log.get("response_time"),
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
        QuickCommerceProduct.objects.filter(search=search_obj).delete()
        return
    incoming_ids = set()
    incoming_map = {}

    for item in results:
        product_uid = item.get("id")
        if not product_uid:
            continue
        product_uid = str(product_uid).strip()
        incoming_ids.add(product_uid)
        incoming_map[product_uid] = item

    existing_products = list(
        QuickCommerceProduct.objects.filter(search=search_obj)
    )

    existing_map = {
        p.product_uid: p
        for p in existing_products
    }

    to_create = []
    to_update = []

    platform = search_obj.platform
    keyword = search_obj.keyword
    pincode = search_obj.pincode

    for product_uid, item in incoming_map.items():
        detail = item.get("detail_data", {})
        defaults = {
            "rank": item.get("rank"),
            "title": item.get("product_title"),
            "brand": item.get("brand"),
            "category": item.get("category"),
            "availability": item.get("availability"),
            "msrp": normalize_price(item.get("msrp")),
            "sell_price": normalize_price(detail.get("sell_price")),
            "rating": normalize_rating(detail.get("rating")),
            "reviews": normalize_reviews(detail.get("reviews")),
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
                    search=search_obj,
                    product_uid=product_uid,
                    **defaults
                )
            )

    if to_create:
        QuickCommerceProduct.objects.bulk_create(
            to_create,
            batch_size=500
        )

    if to_update:
        QuickCommerceProduct.objects.bulk_update(
            to_update,
            fields=[
                "rank", "title", "brand", "category",
                "availability", "msrp", "sell_price",
                "rating", "reviews", "product_url",
                "thumbnail", "main_image",
                "platform", "keyword", "pincode"
            ],
            batch_size=500
        )

    QuickCommerceProduct.objects.filter(
        keyword=search_obj.keyword,
        pincode=search_obj.pincode,
        platform=search_obj.platform
    ).exclude(
        product_uid__in=incoming_ids,
        search=search_obj
    ).delete()
    _sync_product_details(search_obj, incoming_map)
    logger.info(
        f"Products Sync Done | "
        f"Created={len(to_create)} "
        f"Updated={len(to_update)} "
        f"Deleted={max(0, len(existing_products) - len(incoming_ids))}"
    )

def _sync_product_details(search_obj, incoming_map):
    products = list(QuickCommerceProduct.objects.filter(search=search_obj))
    detail_map = {
        d.product_id: d
        for d in QuickCommerceProductDetail.objects.filter(
            product__in=products
        )
    }

    to_create = []
    to_update = []

    for product in products:
        item = incoming_map.get(product.product_uid)
        if not item:
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
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(response, f, ensure_ascii=False, indent=2)
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
    task.save(update_fields=["extra_context"])
    logger.info(f"Saved JSON → {filepath}")
    return str(relative_path), file_size
