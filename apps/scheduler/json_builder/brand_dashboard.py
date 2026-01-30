
import logging
import time
from apps.scheduler.json_builder.utils import save_json_to_file, mysql_connection
from django.utils import timezone
from apps.scheduler.exceptions import DataProcessingException
from apps.scheduler.enums import QuickCommercePlatforms, MarketplacePlatforms

logger = logging.getLogger(__name__)


def _parse_price(val):
    try:
        if val is None:
            return None
        s = str(val)
        # remove currency symbols and commas
        s = s.replace('Rs.', '').replace('₹', '').replace(',', '').strip()
        # remove other non-numeric chars
        import re
        s = re.sub(r'[^0-9\.\-]', '', s)
        return float(s) if s not in ('', None) else None
    except Exception:
        return None


def brand_dashboard_data_builder(task, brand_id=None, brand_name=None, template='brand_dashboard', platform_type=None):
    """Build Brand Dashboard JSON using a MySQL connection provided in task.extra_context['db'].
    Expected DB creds in task.extra_context['db']:
      { 'host', 'port', 'user', 'password', 'database' }
    If creds not provided, raises an informative exception.
    """
    logger.info(f"Starting BRAND_DASHBOARD JSON build for task {getattr(task, 'id', 'unknown')}")
    ctx = task.extra_context or {}
    brand_id = ctx.get('brand_id') or brand_id or getattr(task, 'entity_id', None)
    brand_name = ctx.get('brand_name') or brand_name or f"brand-{brand_id or 'unknown'}"
    platform_type = ctx.get('platform_type') or platform_type

    platforms_live = 0
    if "marketplace" in platform_type:
        platforms_live += len(MarketplacePlatforms)
    if "quick_commerce" in platform_type:
        platforms_live += len(QuickCommercePlatforms)
    
    
    try:
        with mysql_connection() as conn:
            with conn.cursor() as cur:
                # total products for brand
                cur.execute('SELECT COUNT(*) as cnt FROM products WHERE brand=%s', (brand_name,))
                total_products = cur.fetchone().get('cnt', 0)

                # pages available (is_active flag)
                cur.execute('SELECT COUNT(*) as cnt FROM products WHERE brand=%s AND is_active=1', (brand_name,))
                pages_available = cur.fetchone().get('cnt', 0)

                # skus
                cur.execute('SELECT COUNT(DISTINCT sku) as cnt FROM products WHERE brand=%s', (brand_name,))
                average_skus = cur.fetchone().get('cnt', 0)

                # videos
                cur.execute("SELECT COUNT(*) as cnt FROM products WHERE brand=%s AND COALESCE(NULLIF(video_urls, ''), '') <> ''", (brand_name,))
                total_videos = cur.fetchone().get('cnt', 0)

                # average discount: fetch pairs and compute in python (robust to strings)
                cur.execute('SELECT price, sale_price FROM products WHERE brand=%s', (brand_name,))
                rows = cur.fetchall()
                discounts = []
                ratings = []
                images_count = 0
                for r in rows:
                    p = _parse_price(r.get('price'))
                    sp = _parse_price(r.get('sale_price'))
                    if p and sp and p > 0:
                        discounts.append((p - sp) / p)
                    # collect rating
                    try:
                        rt = r.get('rating')
                        if rt is not None:
                            ratings.append(float(rt))
                    except Exception:
                        pass
                    imgs = r.get('image_urls')
                    if imgs and str(imgs).strip():
                        images_count += 1

                avg_discount = (sum(discounts) / len(discounts) * 100) if discounts else 0
                avg_discount_str = f"{round(avg_discount,1)}%" if discounts else "0%"

                avg_rating = int(sum(ratings) / len(ratings)) if ratings else 0

                # pages_live percentage and health score
                pages_live_pct = int((pages_available / total_products * 100) if total_products else 0)
                health_score = avg_rating

                # scorecard approximations
                marketing_content_pct = int((images_count / total_products * 100) if total_products else 0)
                # keyword_analysis: distinct keywords associated
                cur.execute('SELECT COUNT(DISTINCT pr.keyword_id) as cnt FROM product_rankings pr JOIN products p ON pr.product_id = p.id WHERE p.brand=%s', (brand_name,))
                keyword_count = cur.fetchone().get('cnt', 0)
                keyword_analysis = keyword_count
                product_assets_pct = marketing_content_pct
                product_sentiment = avg_rating

        dashboard_data = {
            "overview": {
                'platforms_live': platforms_live,
                'last_update': timezone.now().date().isoformat()
            },
            "market_snapshot": {
                "pages_available": {
                    "value": 12450,
                    "change": "+15% vs overall"
                },
                "average_discount": {
                    "value": "18.5%",
                    "change": "+3.2% vs overall"
                },
                "average_skus": {
                    "value": 2840,
                    "change": "+12% vs overall"
                },
                "total_videos": {
                    "value": 1250,
                    "change": "+8% views"
                }
            },
            "status_check": {
                "pages_live": {
                    "value": "100%",
                    "progress": 100,
                    "tested": "100% of SKUs Tested"
                },
                "health_score": {
                    "value": 61,
                    "progress": 61,
                    "tested": "100% of SKUs Tested"
                },
                "page_accuracy": {
                    "value": "--",
                    "progress": 0,
                    "tested": "0% of SKUs Tested"
                },
                "critical_flags": {
                    "value": "--",
                    "progress": 0,
                    "tested": "0% of SKUs Tested"
                }
            },
            "scorecard_summary": {
                "marketing_content": {
                    "value": 53,
                    "progress": 53,
                    "tested": "100% of SKUs Tested"
                },
                "keyword_analysis": {
                    "value": "--",
                    "progress": 0,
                    "tested": "0% of SKUs Tested"
                },
                "product_assets": {
                    "value": 97,
                    "progress": 97,
                    "tested": "100% of SKUs Tested"
                },
                "product_sentiment": {
                    "value": 33,
                    "progress": 33,
                    "tested": "100% of SKUs Tested"
                }
            }
        }
        logger.info(f"Completed BRAND_DASHBOARD JSON build for task {getattr(task, 'id', 'unknown')}")
        return save_json_to_file(task, dashboard_data, brand_id, brand_name, template)
    except Exception as exc:
        logger.exception("BRAND_DASHBOARD JSON failed")
        raise DataProcessingException (
            message="Brand dashboard JSON build failed",
            extra={
                "brand_id": brand_id,
                "brand_name": brand_name,
                "template": template,
                "error": str(exc)
            }
        )
