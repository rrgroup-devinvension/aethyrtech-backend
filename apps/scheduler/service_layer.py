"""
Service layer for scheduler operations.
Handles job creation, task generation, and entity tracking.
"""
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from apps.scheduler.models import (
    Scheduler,
    SchedulerJob, Task,
    KeywordPincode, BrandJsonFile
)
from celery.result import AsyncResult
from apps.brand.models import Brand
from apps.category.models import Category, CategoryKeyword, CategoryPincode
import logging
from .utility.service_utility import bulk_create_tasks, update_job_status, ensure_brand_json_files, ensure_keyword_pincode_single, update_entity_tracking_on_complete
from apps.scheduler.tasks import process_scheduler_job
from apps.scheduler.enums import JsonTemplate

logger = logging.getLogger(__name__)

@transaction.atomic
def create_job_and_tasks(
    triggered_by='ADMIN',
    scope_type='GLOBAL',
    scope_id=None,
    task_group='JSON_BUILD',
    scheduler_id=None,
    keyword_id=None,
):
    """
    Create a SchedulerJob and generate tasks based on scope.
    
    Args:
        triggered_by: SYSTEM or ADMIN
        scope_type: GLOBAL, KEYWORD, PINCODE, BRAND, JSON
        scope_id: ID of the scoped entity
        task_group: DATA_DUMP, JSON_BUILD, or BOTH
        scheduler_id: Optional - ID of scheduler if triggered by cron
    
    Returns:
        SchedulerJob instance
    """
    # Normalize scope_id for certain scope types. For KEYWORD scope, accept numeric
    # id from callers but store the keyword text in SchedulerJob.scope_id so the
    # job is identifiable by keyword string.
    scope_value = scope_id
    if scope_type == SchedulerJob.ScopeType.KEYWORD and scope_id is not None:
        # If numeric id supplied, resolve to CategoryKeyword.keyword
        try:
            # allow both numeric and string ids; if already a string keyword, keep it
            if isinstance(scope_id, int) or (isinstance(scope_id, str) and scope_id.isdigit()):
                kw = CategoryKeyword.objects.get(id=int(scope_id))
                scope_value = kw.keyword
            else:
                # assume provided value is already the keyword text
                scope_value = str(scope_id)
        except CategoryKeyword.DoesNotExist:
            # fallback: store stringified scope_id
            scope_value = str(scope_id)
    elif scope_type == SchedulerJob.ScopeType.PINCODE and scope_id is not None:
        # For PINCODE jobs, store the real pincode string in job.scope_id while
        # keeping the original scope_id (category_pincode id) for task generation.
        try:
            if isinstance(scope_id, int) or (isinstance(scope_id, str) and scope_id.isdigit()):
                cp = CategoryPincode.objects.get(id=int(scope_id))
                # If a specific keyword was provided for this pincode-run, encode both
                # pincode and keyword into the job.scope_id so we can later distinguish
                # a pincode-wide run from a keyword+pincode run.
                if keyword_id:
                    try:
                        kw = CategoryKeyword.objects.get(id=int(keyword_id))
                        scope_value = f"{cp.pincode}::KW::{kw.keyword}"
                    except CategoryKeyword.DoesNotExist:
                        scope_value = cp.pincode
                else:
                    scope_value = cp.pincode
            else:
                scope_value = str(scope_id)
        except CategoryPincode.DoesNotExist:
            scope_value = str(scope_id)

    # Create the job
    job = SchedulerJob.objects.create(
        scheduler_id=scheduler_id,
        triggered_by=triggered_by,
        scope_type=scope_type,
        scope_id=scope_value,
        task_group=task_group,
        status=SchedulerJob.JobStatus.RUNNING,
        started_at=timezone.now(),
    )

    # Generate tasks based on scope and task_group
    if task_group in [SchedulerJob.TaskGroup.DATA_DUMP]:
        _create_data_dump_tasks(job, scope_type, scope_id, keyword_id)
    
    if task_group in [SchedulerJob.TaskGroup.JSON_BUILD]:
        _create_json_build_tasks(job, scope_type, scope_id)

    # Dispatch to Celery
    try:
        # Try async first (production with broker)
        process_scheduler_job.apply_async((job.id,))
    except Exception as e:
        logger.warning(f"Celery broker not available, running synchronously: {e}")
        # Fall back to synchronous execution (development without broker)
        process_scheduler_job(job.id)
    
    return job


def _create_data_dump_tasks(job, scope_type, scope_id, keyword_id=None):
    """Create DATA_DUMP tasks based on scope."""

    tasks_to_create = []

    # ----------------------
    # GLOBAL SCOPE
    # ----------------------
    if scope_type == SchedulerJob.ScopeType.GLOBAL:

        keywords = CategoryKeyword.objects.filter(
            category__is_deleted=False,
            category__platform_type__contains=["quick_commerce"]
        ).select_related('category').prefetch_related(
            'category__category_pincodes'
        )
        grouped_keywords = {}

        for kw in keywords:

            key = kw.keyword.strip().lower()
            if key not in grouped_keywords:
                grouped_keywords[key] = {
                    'keyword_text': kw.keyword,
                    'platforms': set(),
                    'categories': set()
                }
            if kw.platform:
                grouped_keywords[key]['platforms'].add(kw.platform)
            grouped_keywords[key]['categories'].add(kw.category)
        for data in grouped_keywords.values():
            keyword_text = data['keyword_text']
            platforms = list(data['platforms'])
            categories = data['categories']
            pincodes_seen = set()
            for category in categories:
                for cp in category.category_pincodes.all():
                    if not cp.pincode:
                        continue
                    if cp.pincode in pincodes_seen:
                        continue
                    pincodes_seen.add(cp.pincode)
                    kp = ensure_keyword_pincode_single(keyword_text, cp)

                    tasks_to_create.append({
                        'task_type': Task.TaskType.DATA_DUMP,
                        'entity_type': Task.EntityType.KEYWORD_PINCODE,
                        'entity_id': kp.id,
                        'entity_name': f"{keyword_text} - {cp.pincode}",
                        'extra_context': {
                            'keyword': keyword_text,
                            'pincode': cp.pincode,
                            'platforms': platforms
                        }
                    })
    elif scope_type == SchedulerJob.ScopeType.KEYWORD:

        try:
            category_keyword = CategoryKeyword.objects.select_related('category').get(
                id=scope_id,
                category__is_deleted=False,
                category__platform_type__contains=["quick_commerce"]
            )

            pincodes = CategoryPincode.objects.filter(
                category=category_keyword.category
            ).order_by('pincode')

            frameworks = []
            if category_keyword.platform:
                frameworks.append(category_keyword.platform)
            for cp in pincodes:

                if not cp.pincode:
                    continue

                kp = ensure_keyword_pincode_single(category_keyword.keyword, cp)

                tasks_to_create.append({
                    'task_type': Task.TaskType.DATA_DUMP,
                    'entity_type': Task.EntityType.KEYWORD_PINCODE,
                    'entity_id': kp.id,
                    'entity_name': f"{category_keyword.keyword} - {cp.pincode}",
                    'extra_context': {
                        'keyword': category_keyword.keyword,
                        'pincode': cp.pincode,
                        'frameworks': frameworks
                    }
                })

        except CategoryKeyword.DoesNotExist:
            logger.error(f"CategoryKeyword with id {scope_id} not found or invalid")

    # ----------------------
    # PINCODE SCOPE
    # ----------------------
    elif scope_type == SchedulerJob.ScopeType.PINCODE:

        try:
            category_pincode = CategoryPincode.objects.select_related('category').get(
                id=scope_id,
                category__platform_type__contains=["quick_commerce"],
                category__is_deleted=False
            )

            # ---------- Single Keyword ----------
            if keyword_id:

                try:
                    kw = CategoryKeyword.objects.get(
                        id=int(keyword_id),
                        category=category_pincode.category,
                        category__platform_type__contains=["quick_commerce"]
                    )

                    frameworks = []
                    if kw.platform:
                        frameworks.append(kw.platform)
                    kp = ensure_keyword_pincode_single(kw.keyword, category_pincode)

                    tasks_to_create.append({
                        'task_type': Task.TaskType.DATA_DUMP,
                        'entity_type': Task.EntityType.KEYWORD_PINCODE,
                        'entity_id': kp.id,
                        'entity_name': f"{kw.keyword} - {category_pincode.pincode}",
                        'extra_context': {
                            'keyword': kw.keyword,
                            'pincode': category_pincode.pincode,
                            'frameworks': frameworks
                        }
                    })

                except CategoryKeyword.DoesNotExist:
                    logger.error(f"Invalid keyword {keyword_id} for pincode {scope_id}")

            # ---------- All Keywords ----------
            else:

                keywords = CategoryKeyword.objects.filter(
                    category=category_pincode.category,
                    category__platform_type__contains=["quick_commerce"]
                )
                grouped_keywords = {}

                for kw in keywords:

                    key = kw.keyword.strip().lower()
                    if key not in grouped_keywords:
                        grouped_keywords[key] = {
                            'keyword_text': kw.keyword,
                            'frameworks': set()
                        }
                    if kw.platform:
                        grouped_keywords[key]['frameworks'].add(kw.platform)
                for data in grouped_keywords.values():
                    keyword_text = data['keyword_text']
                    frameworks = list(data['frameworks'])
                    kp = ensure_keyword_pincode_single(keyword_text, category_pincode)

                    tasks_to_create.append({
                        'task_type': Task.TaskType.DATA_DUMP,
                        'entity_type': Task.EntityType.KEYWORD_PINCODE,
                        'entity_id': kp.id,
                        'entity_name': f"{keyword_text} - {category_pincode.pincode}",
                        'extra_context': {
                            'keyword': keyword_text,
                            'pincode': category_pincode.pincode,
                            'frameworks': frameworks
                        }
                    })

        except CategoryPincode.DoesNotExist:
            logger.error(f"CategoryPincode with id {scope_id} not found or invalid")

    # ----------------------
    # BULK CREATE
    # ----------------------
    bulk_create_tasks(job, tasks_to_create)

def _create_json_build_tasks(job, scope_type, scope_id):
    """Create JSON_BUILD tasks based on scope."""
    tasks_to_create = []
    json_templates = [t.slug for t in JsonTemplate]
    
    if scope_type == SchedulerJob.ScopeType.GLOBAL:
        # Create tasks for all brands and all templates
        brands = Brand.objects.filter(is_deleted=False)
        for brand in brands:
            # Ensure BrandJsonFile records exist
            ensure_brand_json_files(brand, json_templates)
            tasks_to_create.append({
                'task_type': Task.TaskType.JSON_BUILD,
                'entity_type': Task.EntityType.JSON_FILE,
                'entity_id': brand.id,
                'entity_name': f"{brand.name}",
                'extra_context': {
                    'brand_id': brand.id,
                    'brand_name': brand.name,
                    'platform_type': getattr(brand.category, 'platform_type'),
                }
            })
    
    elif scope_type == SchedulerJob.ScopeType.BRAND:
        # Create tasks for all templates for this brand
        try:
            brand = Brand.objects.get(id=scope_id)
            # Ensure BrandJsonFile records exist
            ensure_brand_json_files(brand, json_templates)
            tasks_to_create.append({
                'task_type': Task.TaskType.JSON_BUILD,
                'entity_type': Task.EntityType.JSON_FILE,
                'entity_id': brand.id,
                'entity_name': f"{brand.name}",
                'extra_context': {
                    'brand_id': brand.id,
                    'brand_name': brand.name,
                    'platform_type': getattr(brand.category, 'platform_type'),
                }
            })
        except Brand.DoesNotExist:
            logger.error(f"Brand with id {scope_id} not found")
    
    # Bulk create tasks
    bulk_create_tasks(job, tasks_to_create)


# ============================================================================
# Job and Task Status Management
# ============================================================================

def stop_job(job_id):
    """Stop a running job and all its tasks."""
    try:
        job = SchedulerJob.objects.get(id=job_id)
    except SchedulerJob.DoesNotExist:
        return None
    
    if job.status != SchedulerJob.JobStatus.RUNNING:
        return job
    
    # Update job status
    job.status = SchedulerJob.JobStatus.STOPPED
    job.ended_at = timezone.now()
    job.save(update_fields=['status', 'ended_at'])
    
    # Stop all pending/running tasks
    tasks = job.tasks.filter(status__in=[Task.TaskStatus.PENDING, Task.TaskStatus.RUNNING])
    for task in tasks:
        stop_task(task.id)
    
    return job


def stop_task(task_id):
    """Stop a single task."""
    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return None
    
    if task.status not in [Task.TaskStatus.PENDING, Task.TaskStatus.RUNNING]:
        return task

    # If there is an associated celery background task, attempt to revoke it
    if getattr(task, 'celery_task_id', None):
        try:
            res = AsyncResult(task.celery_task_id)
            # revoke; terminate worker if running
            res.revoke(terminate=True)
        except Exception:
            logger.exception(f"Failed to revoke celery task {task.celery_task_id} for task {task.id}")

    task.status = Task.TaskStatus.STOPPED
    task.ended_at = timezone.now()
    task.error_message = 'Stopped by user'
    task.save(update_fields=['status', 'ended_at', 'error_message'])
    
    # Update entity tracking
    update_entity_tracking_on_complete(task, success=False, error_msg='Stopped by user')
    
    # Update parent job status
    if task.scheduler_job:
        update_job_status(task.scheduler_job)
    return task

