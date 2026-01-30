
import logging
import time
from apps.scheduler.json_builder.utils import save_json_to_file, mysql_connection
from django.utils import timezone
from datetime import datetime, timedelta
from apps.scheduler.utility.tasks_utility import get_brands
import random
import math

logger = logging.getLogger(__name__)


def category_view_data_builder(task, brand_id=None, brand_name=None, template='category_view', platform_type=None):
    """Build category view JSON and save."""
    logger.info(f"Starting CATEGORY_VIEW JSON build for task {getattr(task, 'id', 'unknown')}")
    time.sleep(1)

    ctx = task.extra_context or {}
    brand_id = ctx.get('brand_id') or brand_id or getattr(task, 'entity_id', None)
    brand_name = ctx.get('brand_name') or brand_name or f"brand-{brand_id or 'unknown'}"
    platform_type = ctx.get('platform_type') or platform_type
    brands = get_brands(brand_id)

    # Build payload using DB aggregates
    try:
        with mysql_connection() as conn:
            with conn.cursor() as cur:
                # Determine brand category (if any)
                cur.execute('SELECT category FROM products WHERE brand=%s LIMIT 1', (brand_name,))
                row = cur.fetchone()
                brand_category = row.get('category') if row else None

                # Fetch all products for this brand
                cur.execute('SELECT id, sku, price, sale_price, rating, image_urls, video_urls, is_active, created_at FROM products WHERE brand=%s', (brand_name,))
                prod_rows = cur.fetchall()

                # Helper to parse price strings to float
                def _parse_price(val):
                    try:
                        if val is None:
                            return None
                        s = str(val)
                        s = s.replace('Rs.', '').replace('₹', '').replace(',', '').strip()
                        import re
                        s = re.sub(r'[^0-9\.\-]', '', s)
                        return float(s) if s not in ('', None) else None
                    except Exception:
                        return None

                prices = [p for p in (_parse_price(r.get('price')) for r in prod_rows) if p]
                avg_price = (sum(prices) / len(prices)) if prices else 0

                # Prepare last 8 months buckets (oldest -> newest)
                today = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                months = []
                for i in range(7, -1, -1):
                    m = (today - timedelta(days=30 * i))
                    months.append(m)

                sales_traditional = [0] * 8
                sales_premium = [0] * 8

                for r in prod_rows:
                    created = r.get('created_at')
                    price = _parse_price(r.get('price')) or 0
                    if not created:
                        continue
                    for idx, m in enumerate(months):
                        start = m
                        # rough month end = start + 31 days
                        end = start + timedelta(days=31)
                        if start <= created < end:
                            if avg_price and price >= avg_price:
                                sales_premium[idx] += 1
                            else:
                                sales_traditional[idx] += 1
                            break

                # Format sales_by_month similar to example
                sales_by_month = {
                    'chart_id': 'salesChart',
                    'title': 'Sales by Month',
                    'report': [
                        {'internalName': 'traditional', 'label': 'Traditional', 'values': sales_traditional},
                        {'internalName': 'premium', 'label': 'Premium', 'values': sales_premium},
                    ]
                }

                # Top brands in same category (for category_data and availability/top_brands)
                if brand_category:
                    cur.execute('''
                        SELECT brand, COUNT(*) as sku, SUM(CASE WHEN is_active=1 THEN 1 ELSE 0 END) as live, 
                               AVG(COALESCE(rating,0)) as avg_rating, SUM(COALESCE(review_count,0)) as reviews,
                               SUM(CASE WHEN video_urls IS NOT NULL AND video_urls <> '' THEN 1 ELSE 0 END) as videos
                        FROM products
                        WHERE category=%s
                        GROUP BY brand
                        ORDER BY sku DESC
                        LIMIT 5
                    ''', (brand_category,))
                else:
                    cur.execute('''
                        SELECT brand, COUNT(*) as sku, SUM(CASE WHEN is_active=1 THEN 1 ELSE 0 END) as live, 
                               AVG(COALESCE(rating,0)) as avg_rating, SUM(COALESCE(review_count,0)) as reviews,
                               SUM(CASE WHEN video_urls IS NOT NULL AND video_urls <> '' THEN 1 ELSE 0 END) as videos
                        FROM products
                        GROUP BY brand
                        ORDER BY sku DESC
                        LIMIT 5
                    ''')

                brands_rows = cur.fetchall()

                # category_data: pick top 4 brands and present audit-like rows
                category_data = []
                for b in brands_rows[:4]:
                    total = int(b.get('sku') or 0)
                    live = int(b.get('live') or 0)
                    percent_live = f"{int((live / total * 100) if total else 0)}%"
                    avg_health = int(math.floor(b.get('avg_rating') or 0))
                    category_data.append({
                        'audit_name': b.get('brand'),
                        'frequency': 'One Time',
                        'skus': total,
                        'last_run': timezone.now().strftime('%m/%d/%Y'),
                        'percent_live': percent_live,
                        'avg_health': avg_health,
                    })

                # availability: top 3 brands
                availability = []
                for b in brands_rows[:3]:
                    total = int(b.get('sku') or 0)
                    not_available = total - int(b.get('live') or 0)
                    availability.append({'brand': b.get('brand'), 'sku': total, 'not_available': not_available})

                # top_keywords: keywords for this brand from product_rankings
                # compute counts for last 30 days and previous 30 days to show trend
                now = datetime.utcnow()
                recent_cut = now - timedelta(days=30)
                prev_cut = now - timedelta(days=60)
                cur.execute('''
                    SELECT k.keyword as keyword,
                           COUNT(DISTINCT pr.product_id) as cnt,
                           SUM(CASE WHEN pr.created_at >= %s THEN 1 ELSE 0 END) as recent_cnt,
                           SUM(CASE WHEN pr.created_at >= %s AND pr.created_at < %s THEN 1 ELSE 0 END) as prev_cnt
                    FROM product_rankings pr
                    JOIN keywords k ON pr.keyword_id = k.id
                    JOIN products p ON pr.product_id = p.id
                    WHERE p.brand=%s
                    GROUP BY k.keyword
                    ORDER BY cnt DESC
                    LIMIT 4
                ''', (recent_cut, prev_cut, recent_cut, brand_name))
                kw_rows = cur.fetchall()
                top_keywords = []
                for kw in kw_rows:
                    cur_cnt = int(kw.get('recent_cnt') or 0)
                    prev_cnt = int(kw.get('prev_cnt') or 0)
                    trend = ''
                    trend_type = 'neutral'
                    if prev_cnt:
                        try:
                            pct = int((cur_cnt - prev_cnt) / prev_cnt * 100)
                            trend = f"{pct}%"
                            trend_type = 'positive' if pct > 0 else ('negative' if pct < 0 else 'neutral')
                        except Exception:
                            trend = ''
                    elif cur_cnt:
                        trend = '+100%'
                        trend_type = 'positive'

                    top_keywords.append({'keyword': kw.get('keyword'), 'search_volume': kw.get('cnt') or 0, 'trend': trend, 'trend_type': trend_type})

                # # top_brands: build list similar to sample with avg_discount, avg_price, rating, reviews, videos
                # top_brands = []
                # for b in brands_rows[:3]:
                #     brand_name_b = b.get('brand')
                #     # fetch price/sale_price for this brand to compute avg_discount and avg_price
                #     cur.execute('SELECT price, sale_price FROM products WHERE brand=%s LIMIT 1000', (brand_name_b,))
                #     pr_rows = cur.fetchall()
                #     prices = []
                #     discounts = []
                #     for pr in pr_rows:
                #         p = _parse_price(pr.get('price'))
                #         sp = _parse_price(pr.get('sale_price'))
                #         if p:
                #             prices.append(p)
                #         if p and sp and p > 0:
                #             discounts.append((p - sp) / p)

                #     avg_price_val = int(sum(prices) / len(prices)) if prices else 0
                #     avg_discount_str = f"{int(round((sum(discounts) / len(discounts) * 100) if discounts else 0))}% avg discount"
                #     top_brands.append({
                #         'name': brand_name_b,
                #         'avg_discount': avg_discount_str,
                #         'avg_price': f"₹{avg_price_val:,}" if avg_price_val else 'N/A',
                #         'rating': float(b.get('avg_rating') or 0),
                #         'reviews': int(b.get('reviews') or 0),
                #         'videos': int(b.get('videos') or 0),
                #     })

        top_brands = []
        for b in brands:
            top_brands.append({
                "name": b,
                "avg_discount": "15% avg discount",
                "avg_price": "₹20,243",
                "rating": round(random.uniform(3.5,4.8),1),
                "reviews": random.randint(500,1500),
                "videos": random.randint(10,100),
            })

        payload = {
            "sales_by_month": {
                "chart_id": "salesChart",
                "title": "Sales by Month",
                "report": [
                {
                    "internalName": "traditional",
                    "label": "Traditional",
                    "values": [310, 300, 370, 295, 350, 300, 230, 290]
                },
                {
                    "internalName": "premium",
                    "label": "Premium",
                    "values": [150, 230, 195, 260, 220, 300, 320, 490]
                }
                ]
            },
            "category_data": [
                {
                "audit_name": "HP Printer",
                "frequency": "One Time",
                "skus": 72,
                "last_run": "08/24/2025",
                "percent_live": "100%",
                "avg_health": 62
                },
                {
                "audit_name": "Brother Printer",
                "frequency": "One Time",
                "skus": 57,
                "last_run": "08/24/2025",
                "percent_live": "100%",
                "avg_health": 64
                },
                {
                "audit_name": "Canon Printer",
                "frequency": "One Time",
                "skus": 65,
                "last_run": "08/24/2025",
                "percent_live": "100%",
                "avg_health": 62
                },
                {
                "audit_name": "Category",
                "frequency": "One Time",
                "skus": 194,
                "last_run": "08/24/2025",
                "percent_live": "100%",
                "avg_health": 72
                }
            ],
            "availability": [
                {
                "brand": "HP",
                "sku": 72,
                "not_available": 7
                },
                {
                "brand": "Canon",
                "sku": 65,
                "not_available": 22
                },
                {
                "brand": "Brother",
                "sku": 57,
                "not_available": 5
                }
            ],
            "top_keywords": [
                {
                "keyword": "HP",
                "search_volume": 210000,
                "trend": "+12%",
                "trend_type": "positive"
                },
                {
                "keyword": "printer hp",
                "search_volume": 60500,
                "trend": "+15%",
                "trend_type": "positive"
                },
                {
                "keyword": "printer driver",
                "search_volume": 60500,
                "trend": "+22%",
                "trend_type": "positive"
                },
                {
                "keyword": "canon printer",
                "search_volume": 49500,
                "trend": "+18%",
                "trend_type": "positive"
                }
            ],
            "top_brands": top_brands
        }

        return save_json_to_file(task, payload, brand_id, brand_name, template)
    except Exception:
        logger.exception('Failed to build CATEGORY_VIEW JSON')
        raise
    logger.info(f"Completed CATEGORY_VIEW JSON build for task {getattr(task, 'id', 'unknown')}")