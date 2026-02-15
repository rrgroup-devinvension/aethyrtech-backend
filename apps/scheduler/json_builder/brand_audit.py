
import logging
from apps.scheduler.json_builder.utils import save_json_to_file
from apps.scheduler.exceptions import DataProcessingException
from apps.scheduler.enums import JsonTemplate
from apps.scheduler.utility.tasks_utility import match_brand
from datetime import datetime, date

logger = logging.getLogger(__name__)

from apps.scheduler.utility.jsonbuilder_api_logger import log_start, log_success, log_error


from datetime import datetime


def get_audit_data(brands, products):
    """
    Build brand audit table rows.

    Metrics:
    - SKU count per brand
    - Live availability %
    - Average health score
    - Last run date (latest scraped_date if available)
    - Status class based on health score
    """

    rows = []

    for brand in brands:
        sku_count = 0
        live_count = 0
        health_sum = 0
        health_count = 0
        last_run = None
        found = False

        for p in products:
            if not p.brand or not match_brand(p.brand, brand):
                continue
            found = True
            sku_count += 1
            # Availability
            if (p.availability_status or "").lower() == "available":
                live_count += 1
            # Health score
            try:
                score = p.health_score()
            except Exception:
                score = 0
            health_sum += score
            health_count += 1
            # Last run date
            # Last run date
            if getattr(p, "scraped_date", None):
                sd = p.scraped_date
                # Convert datetime -> date
                if isinstance(sd, datetime):
                    sd = sd.date()
                if not last_run or sd > last_run:
                    last_run = sd
                    if not found:
                        continue
        # ---------- Calculations ----------
        live_percent = 100
        avg_health = round(health_sum / health_count) if health_count else 0
        # Format last run
        if last_run:
            last_run_str = last_run.strftime("%d/%m/%Y")
        else:
            last_run_str = datetime.now().strftime("%d/%m/%Y")

        # Status class (you can tweak thresholds)
        if avg_health < 40:
            status_class = "status-red"
        elif avg_health < 70:
            status_class = "status-yellow"
        else:
            status_class = "status-green"

        rows.append({
            "Audit Name": brand,
            "Frequency": "One Time",
            "SKUs": str(sku_count),
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


def brand_audit_data_builder(brands, keywords, products, task, brand_id=None, brand_name=None, template=JsonTemplate.BRAND_AUDIT.slug, platform_type=None):
    t_id = getattr(task, 'id', 'unknown')
    logger.info(f"Starting BRAND_AUDIT JSON build for task {t_id}")
    log_start(task_id=t_id, info={'template': template, 'brand_id': brand_id})
    try:
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
        return save_json_to_file(task, audit, brand_id, brand_name, template)
    except Exception as exc:
        logger.exception("BRAND_AUDIT JSON failed", exc)
        log_error(task_id=t_id, error=str(exc), extra={'template': template, 'brand_id': brand_id})
        raise DataProcessingException(
            message="Brand audit JSON build failed",
            extra={
                "brand_id": brand_id,
                "brand_name": brand_name,
                "template": template,
                "error": str(exc)
            }
        )

