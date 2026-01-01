"""
Legacy service functions - now using service_layer.py for reusable logic.
These are kept for backward compatibility.
"""
from django.utils import timezone
from .models import Scheduler, SchedulerJob, Task, BrandJsonFile
from .service_layer import (
    create_job_with_tasks,
    auto_update_job_status as _auto_update_job_status,
    resolve_scope_and_create_tasks as _resolve_scope_and_create_tasks,
    sync_files_table_for_brand as _sync_files_table_for_brand,
    update_entity_tracking_on_complete
)
from django.db import transaction
from django.conf import settings
from apps.brand.models import Brand
import os
import json
import logging

logger = logging.getLogger(__name__)


def create_scheduler_job(scheduler_id=None, triggered_by='SYSTEM', scope_type='GLOBAL', scope_id=None, task_group='BOTH'):
    """Create a SchedulerJob and enqueue processing. (Legacy wrapper)"""
    return create_job_with_tasks(
        scheduler_id=scheduler_id,
        triggered_by=triggered_by,
        scope_type=scope_type,
        scope_id=scope_id,
        task_group=task_group
    )


def auto_update_job_status(job: SchedulerJob):
    """Recalc job status based on child tasks. (Legacy wrapper)"""
    return _auto_update_job_status(job)


def resolve_scope_and_create_tasks(job: SchedulerJob):
    """Resolve the scope of a SchedulerJob and create Task rows. (Legacy wrapper)"""
    return _resolve_scope_and_create_tasks(job)


def sync_files_table_for_brand(brand: Brand):
    """Ensure BrandJsonFile entries match configured templates. (Legacy wrapper)"""
    return _sync_files_table_for_brand(brand)


def build_and_save_json_for_task(task: Task, payload: dict):
    """Helper to write JSON payload to MEDIA and update task.extra_context with filename/path."""
    media_sub = getattr(settings, 'SCHEDULER_JSON_MEDIA_SUBPATH', 'jsons')
    brand_id = (task.entity_id or payload.get('brand_id'))
    brand_folder = f"brand-{brand_id}"
    folder = os.path.join(settings.MEDIA_ROOT, media_sub, brand_folder)
    os.makedirs(folder, exist_ok=True)

    # filename pattern: brand-brand-name-{id}-{type}-{timestamp}.json
    safe_name = str(task.entity_name).replace(' ', '-')
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    filename = f"brand-{safe_name}-{brand_id}-{task.task_type}-{timestamp}.json"
    path = os.path.join(folder, filename)

    # write file
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    # update task.extra_context
    task.extra_context = {**(task.extra_context or {}), 'filename': filename, 'file_path': os.path.join(media_sub, brand_folder, filename)}
    task.save(update_fields=['extra_context'])
    
    # Update BrandJsonFile record and tracking
    try:
        tpl = (task.extra_context or {}).get('template')
        if tpl and task.entity_id:
            bobj, _ = BrandJsonFile.objects.get_or_create(brand_id=task.entity_id, template=tpl)
            bobj.filename = filename
            bobj.file_path = os.path.join(media_sub, brand_folder, filename)
            bobj.save(update_fields=['filename', 'file_path'])
            
            # Use service_layer for tracking
            update_entity_tracking_on_complete(task, success=True)
    except Exception:
        logger.exception('Failed to update BrandJsonFile after saving JSON for task %s', task.id)

    return task


def _ensure_crontab_schedule(cron_expression: str):
    """Parse a cron expression (5 fields) and return or create a CrontabSchedule.
    If django_celery_beat is not installed, return None.
    """
    try:
        from django_celery_beat.models import CrontabSchedule
    except Exception:
        logger.warning('django_celery_beat not installed; skipping crontab creation')
        return None

    parts = cron_expression.split()
    if len(parts) != 5:
        logger.warning('Invalid cron expression: %s', cron_expression)
        return None
    minute, hour, day_of_month, month_of_year, day_of_week = parts
    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute=minute,
        hour=hour,
        day_of_month=day_of_month,
        month_of_year=month_of_year,
        day_of_week=day_of_week,
    )
    return schedule


def sync_periodic_task_for_scheduler(scheduler: Scheduler):
    """Create or update a django-celery-beat PeriodicTask for given scheduler if trigger_type==CRON.
    If django-celery-beat is not available, this is a no-op.
    """
    try:
        from django_celery_beat.models import PeriodicTask
    except Exception:
        logger.warning('django_celery_beat not available; skipping periodic task sync')
        return None

    # find or create crontab schedule
    if not scheduler.cron_expression:
        # remove existing periodic task if any
        PeriodicTask.objects.filter(name=f'scheduler-{scheduler.id}').delete()
        return None

    schedule = _ensure_crontab_schedule(scheduler.cron_expression)
    if schedule is None:
        return None

    # args: pass scheduler id so task can create SchedulerJob
    import json as _json
    defaults = {
        'crontab': schedule,
        'task': 'apps.scheduler.tasks.trigger_scheduler',
        'args': _json.dumps([scheduler.id]),
        'enabled': scheduler.status == Scheduler.Status.ACTIVE,
    }
    pt, created = PeriodicTask.objects.update_or_create(name=f'scheduler-{scheduler.id}', defaults=defaults)
    return pt


def remove_periodic_task_for_scheduler(scheduler: Scheduler):
    try:
        from django_celery_beat.models import PeriodicTask
    except Exception:
        return
    PeriodicTask.objects.filter(name=f'scheduler-{scheduler.id}').delete()
