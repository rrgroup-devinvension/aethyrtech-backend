
import logging
import time
from apps.scheduler.json_builder.utils import save_json_to_file, mysql_connection
from django.utils import timezone
from apps.scheduler.exceptions import DataProcessingException

logger = logging.getLogger(__name__)


def brand_audit_data_builder(task, brand_id=None, brand_name=None, template='brand_audit', platform_type=None):
    """Build Brand Audit JSON and save using shared utility.

    Signature keeps optional explicit params but prefers values in `task.extra_context`.
    """
    logger.info(f"Starting BRAND_AUDIT JSON build for task {getattr(task, 'id', 'unknown')}")
    # simulate work
    time.sleep(1)

    ctx = task.extra_context or {}
    brand_id = ctx.get('brand_id') or brand_id or getattr(task, 'entity_id', None)
    brand_name = ctx.get('brand_name') or brand_name or f"brand-{brand_id or 'unknown'}"
    platform_type = ctx.get('platform_type') or platform_type
    try:
        with mysql_connection() as conn:
            with conn.cursor() as cur:
                # primary brand stats
                cur.execute('SELECT COUNT(*) as cnt FROM products WHERE brand=%s', (brand_name,))
                skus = cur.fetchone().get('cnt', 0)

                cur.execute('SELECT COUNT(*) as cnt FROM products WHERE brand=%s AND is_active=1', (brand_name,))
                live = cur.fetchone().get('cnt', 0)

                cur.execute('SELECT AVG(rating) as avg_rating FROM products WHERE brand=%s', (brand_name,))
                avg_rating = cur.fetchone().get('avg_rating') or 0

                # top competitor brands (sample)
                cur.execute('SELECT brand, COUNT(*) as cnt FROM products WHERE brand<>%s GROUP BY brand ORDER BY cnt DESC LIMIT 2', (brand_name,))
                comps = cur.fetchall()

        rows = []
        last_run = timezone.now().strftime('%m/%d/%Y')
        pct_live = f"{int((live / skus * 100) if skus else 0)}%"
        status_class = 'status-green' if int(avg_rating) >= 80 else 'status-yellow' if int(avg_rating) >= 60 else 'status-red'

        rows.append({
            'Audit Name': brand_name,
            'Frequency': 'One Time',
            'SKUs': str(skus),
            'Last Run': last_run,
            '% Live': pct_live,
            'Avg Health': str(int(avg_rating)),
            'View': {'icon': 'fa-solid fa-eye', 'action': 'viewProductCatalog', 'id': brand_name.lower().replace(' ', '-')},
            'statusClass': status_class
        })
        for comp in comps:
            cname = comp.get('brand') or 'competitor'
            cnt = comp.get('cnt', 0)
            comp_pct_live = '100%'
            rows.append({
                'Audit Name': cname,
                'Frequency': 'One Time',
                'SKUs': str(cnt),
                'Last Run': last_run,
                '% Live': comp_pct_live,
                'Avg Health': '0',
                'View': {'icon': 'fa-solid fa-eye', 'action': 'viewProductCatalog', 'id': cname.lower().replace(' ', '-')},
                'statusClass': 'status-red'
            })

        audit = {
            'table': {
                'type': 'table',
                'title': 'My Audits',
                'headers': ['Audit Name', 'Frequency', 'SKUs', 'Last Run', '% Live', 'Avg Health', 'View'],
                'rows': rows
            },
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
        logger.exception("BRAND_AUDIT JSON failed")
        raise DataProcessingException(
            message="Brand audit JSON build failed",
            extra={
                "brand_id": brand_id,
                "brand_name": brand_name,
                "template": template,
                "error": str(exc)
            }
        )

