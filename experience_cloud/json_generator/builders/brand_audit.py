import logging
from datetime import datetime

from experience_cloud.json_generator.decorators import handle_builder_exceptions
from experience_cloud.json_generator.schemas import RegionDataSchema

logger = logging.getLogger(__name__)





def get_audit_data(brands, products):
    """Iterate over the scraped product catalog to aggregate and build high-level brand audit table metrics.

    Calculates aggregated SKU counts, average health scores, and stock availability percentages across all products.
    """
    brand_stats = {brand: {
        "sku_count": 0,
        "live_count": 0,
        "health_sum": 0,
        "health_count": 0,
        "last_run": None
    } for brand in brands}

    for p in products:
        if not p.brand or p.brand not in brand_stats:
            continue

        stats = brand_stats[p.brand]
        stats["sku_count"] += 1

        if (p.availability_status or "").lower() == "available":
            stats["live_count"] += 1

        try:
            score = p.health_score()
        except (ValueError, TypeError, AttributeError):
            score = 0

        stats["health_sum"] += score
        stats["health_count"] += 1

        if getattr(p, "scraped_date", None):
            sd = p.scraped_date
            if not stats["last_run"] or sd > stats["last_run"]:
                stats["last_run"] = sd

    rows = []
    for brand in brands:
        stats = brand_stats[brand]
        live_percent = 100
        avg_health = round(stats["health_sum"] / stats["health_count"]) if stats["health_count"] else 0

        if stats["last_run"]:
            last_run_str = stats["last_run"].strftime("%d/%m/%Y")
        else:
            last_run_str = datetime.now().strftime("%d/%m/%Y")

        if avg_health < 40:
            status_class = "status-red"
        elif avg_health < 70:
            status_class = "status-yellow"
        else:
            status_class = "status-green"

        rows.append({
            "Audit Name": brand,
            "Frequency": "One Time",
            "SKUs": str(stats["sku_count"]),
            "Last Run": last_run_str,
            "% Live": f"{live_percent}%",
            "Avg Health": str(avg_health),
            "View": {
                "icon": "fa-solid fa-eye",
                "action": "viewProductCatalog",
                "id": brand.lower().replace(" ", "_")
            },
            "statusClass": status_class
        })

    return rows


@handle_builder_exceptions
def brand_audit_builder(
    region_data: RegionDataSchema, task, products=None, template="template-name"
) -> tuple[bool, dict]:
    """Construct the JSON payload for the Brand Audit dashboard view, including flagged alerts and KPIs."""
    brands = region_data.get("display_brands", [])

    t_id = getattr(task, 'id', 'unknown')
    logger.info(f"Starting BRAND_AUDIT JSON build for task {t_id}")
    audit_table = {
            'type': 'table',
            'title': 'My Audits',
            'headers': ['Audit Name', 'Frequency', 'SKUs', 'Last Run', '% Live', 'Avg Health', 'View'],
            "rows": get_audit_data(brands, products)
    }
    audit = {
        'table': audit_table,
        'action-items': {
            'type': 'action-items',
            'title': 'Action Items',
            'columns': [
                [
                    {'label': 'Alerts', 'count': '0'},
                    {'label': 'SKUs not found', 'count': '0'}
                ],
                [
                    {'label': 'Missing SKUs', 'count': '0'},
                    {'label': 'Score < 40', 'count': '0'}
                ],
                [
                    {'label': 'Key Items < 60', 'count': '--'},
                    {'label': 'New Launches < 60', 'count': '--'}
                ],
                [
                    {'label': 'Top Sellers < 60', 'count': '--'},
                    {'label': 'High Returns < 60', 'count': '--'}
                ]
            ]
        },
        'flagged-items': {
            'type': 'flagged-items',
            'title': 'Flagged Items',
            'flags': [
                {'level': 'critical', 'icon': 'fas fa-exclamation-triangle', 'text': 'No critical Flags found.'},
                {'level': 'warning', 'icon': 'fas fa-exclamation-triangle', 'text': 'No warning Flags found.'},
                {'level': 'indicator', 'icon': 'fas fa-exclamation-circle', 'text': 'No indicator Flags found.'}
            ]
        }
    }
    logger.info(f"Completed BRAND_AUDIT JSON build for task {getattr(task, 'id', 'unknown')}")
    return False, audit
