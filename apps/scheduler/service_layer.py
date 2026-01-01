"""
Reusable service layer for scheduler operations.
Provides generic functions that work across different entity types (Keyword, BrandJsonFile, etc.)
"""
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from apps.scheduler.models import (
    Scheduler, SchedulerJob, Task,
    Keyword, Pincode, BrandJsonFile
)
from apps.brand.models import Brand
from apps.scheduler.tasks import process_scheduler_job
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Generic Job and Task Management
# ============================================================================

@transaction.atomic
def create_job_with_tasks(
    scheduler_id=None,
    triggered_by='SYSTEM',
    scope_type='GLOBAL',
    scope_id=None,
    task_group='BOTH',
    task_configs=None
):
    """
    Generic function to create a SchedulerJob with tasks.
    
    Args:
        scheduler_id: Optional Scheduler FK
        triggered_by: SYSTEM or ADMIN
        scope_type: GLOBAL, KEYWORD, BRAND, JSON
        scope_id: ID of the scoped entity
        task_group: DATA_DUMP, JSON_BUILD, or BOTH
        task_configs: List of dicts with task configuration
            Example: [
                {
                    'task_type': 'DATA_DUMP',
                    'entity_type': 'KEYWORD',
                    'entity_id': 1,
                    'entity_name': 'laptop - 110001',
                    'extra_context': {'keyword': 'laptop', 'pincode': '110001'}
                }
            ]
    
    Returns:
        SchedulerJob instance
    """
    scheduler = None
    if scheduler_id:
        scheduler = Scheduler.objects.filter(id=scheduler_id).first()

    job = SchedulerJob.objects.create(
        scheduler=scheduler,
        triggered_by=triggered_by,
        scope_type=scope_type,
        scope_id=scope_id,
        task_group=task_group,
        status=SchedulerJob.JobStatus.RUNNING,
        started_at=timezone.now(),
    )

    # Create tasks if provided
    created_tasks = []
    if task_configs:
        for config in task_configs:
            task = Task.objects.create(
                scheduler_job=job,
                task_type=config.get('task_type', Task.TaskType.DATA_DUMP),
                entity_type=config.get('entity_type', Task.EntityType.KEYWORD),
                entity_id=config.get('entity_id'),
                entity_name=config.get('entity_name', ''),
                extra_context=config.get('extra_context'),
                status=Task.TaskStatus.PENDING,
            )
            created_tasks.append(task)

    # Dispatch to Celery
    process_scheduler_job.apply_async((job.id,))
    
    return job


def auto_update_job_status(job: SchedulerJob):
    """
    Recalculate job status based on child tasks.
    - If any task is RUNNING -> job is RUNNING
    - If any task FAILED and some SUCCESS -> PARTIAL
    - If all FAILED -> FAILED
    - If all SUCCESS -> SUCCESS
    """
    tasks = job.tasks.all()
    if not tasks:
        job.status = SchedulerJob.JobStatus.SUCCESS
        job.ended_at = timezone.now()
        job.save()
        return job

    statuses = set(tasks.values_list('status', flat=True))
    
    if any(s == Task.TaskStatus.RUNNING for s in statuses):
        job.status = SchedulerJob.JobStatus.RUNNING
    elif any(s == Task.TaskStatus.FAILED for s in statuses):
        if any(s == Task.TaskStatus.SUCCESS for s in statuses):
            job.status = SchedulerJob.JobStatus.PARTIAL
        else:
            job.status = SchedulerJob.JobStatus.FAILED
        job.ended_at = timezone.now()
    elif all(s == Task.TaskStatus.SUCCESS for s in statuses):
        job.status = SchedulerJob.JobStatus.SUCCESS
        job.ended_at = timezone.now()
    
    job.save()
    return job


@transaction.atomic
def stop_job(job_id):
    """
    Stop a running job and all its pending/running tasks.
    
    Args:
        job_id: SchedulerJob ID
    
    Returns:
        Updated SchedulerJob instance
    """
    try:
        job = SchedulerJob.objects.get(id=job_id)
        
        # Update job status
        job.status = SchedulerJob.JobStatus.FAILED
        job.ended_at = timezone.now()
        job.save()
        
        # Stop all pending/running tasks
        tasks_to_stop = job.tasks.filter(
            status__in=[Task.TaskStatus.PENDING, Task.TaskStatus.RUNNING]
        )
        
        for task in tasks_to_stop:
            task.status = Task.TaskStatus.FAILED
            task.error_message = "Stopped by user"
            task.ended_at = timezone.now()
            task.save()
        
        return job
    except SchedulerJob.DoesNotExist:
        logger.error(f"Job {job_id} not found")
        return None


@transaction.atomic
def stop_task(task_id):
    """
    Stop a single running task.
    
    Args:
        task_id: Task ID
    
    Returns:
        Updated Task instance
    """
    try:
        task = Task.objects.get(id=task_id)
        
        if task.status in [Task.TaskStatus.PENDING, Task.TaskStatus.RUNNING]:
            task.status = Task.TaskStatus.FAILED
            task.error_message = "Stopped by user"
            task.ended_at = timezone.now()
            task.save()
            
            # Update job status
            auto_update_job_status(task.scheduler_job)
        
        return task
    except Task.DoesNotExist:
        logger.error(f"Task {task_id} not found")
        return None


# ============================================================================
# Entity Tracking Management
# ============================================================================

def update_entity_tracking_on_start(task: Task):
    """
    Update entity's last_running_task when task starts.
    Handles both Keyword and BrandJsonFile entities.
    
    Args:
        task: Task instance
    """
    try:
        if task.entity_type == Task.EntityType.KEYWORD and task.entity_id:
            Keyword.objects.filter(id=task.entity_id).update(last_running_task=task)
        elif task.entity_type == Task.EntityType.JSON_FILE:
            # For JSON_FILE, entity_id is brand_id and we need template from extra_context
            brand_id = task.entity_id
            template = (task.extra_context or {}).get('template')
            if brand_id and template:
                BrandJsonFile.objects.filter(
                    brand_id=brand_id, 
                    template=template
                ).update(last_running_task=task)
    except Exception as e:
        logger.exception(f"Failed to update entity tracking on start for task {task.id}: {e}")


def update_entity_tracking_on_complete(task: Task, success=True, error_msg=None):
    """
    Update entity's last_completed_task and other fields when task completes.
    Handles both Keyword and BrandJsonFile entities.
    
    Args:
        task: Task instance
        success: Whether task completed successfully
        error_msg: Error message if task failed
    """
    try:
        now = timezone.now()
        
        if task.entity_type == Task.EntityType.KEYWORD and task.entity_id:
            Keyword.objects.filter(id=task.entity_id).update(
                last_completed_task=task,
                last_synced=now,
                error_message=error_msg if not success else None
            )
        elif task.entity_type == Task.EntityType.JSON_FILE:
            brand_id = task.entity_id
            template = (task.extra_context or {}).get('template')
            if brand_id and template:
                BrandJsonFile.objects.filter(
                    brand_id=brand_id,
                    template=template
                ).update(
                    last_completed_task=task,
                    last_synced=now,
                    error_message=error_msg if not success else None
                )
    except Exception as e:
        logger.exception(f"Failed to update entity tracking on complete for task {task.id}: {e}")


# ============================================================================
# Keyword Sync Operations
# ============================================================================

def resolve_keyword_tasks(job: SchedulerJob):
    """
    Create DATA_DUMP tasks based on scope for keywords.
    
    Scope types:
    - GLOBAL: All active keyword × pincode combinations
    - KEYWORD: All pincodes for a specific keyword ID (scope_id)
    - (Future) KEYWORD+PINCODE: Single keyword × pincode combination
    
    Returns:
        List of created Task objects
    """
    created_tasks = []
    
    if job.scope_type == SchedulerJob.ScopeType.GLOBAL:
        # All active keywords
        keywords = Keyword.objects.filter(is_deleted=False, is_active=True).select_related('pincode')
        
        for kw in keywords:
            task = Task.objects.create(
                scheduler_job=job,
                task_type=Task.TaskType.DATA_DUMP,
                entity_type=Task.EntityType.KEYWORD,
                entity_id=kw.id,
                entity_name=f"{kw.keyword} - {kw.pincode.pincode}",
                extra_context={
                    'keyword': kw.keyword,
                    'pincode': kw.pincode.pincode,
                    'keyword_id': kw.id,
                    'pincode_id': kw.pincode.id
                },
                status=Task.TaskStatus.PENDING,
            )
            created_tasks.append(task)
    
    elif job.scope_type == SchedulerJob.ScopeType.KEYWORD and job.scope_id:
        # All pincodes for specific keyword
        keywords = Keyword.objects.filter(
            id=job.scope_id,
            is_deleted=False,
            is_active=True
        ).select_related('pincode')
        
        for kw in keywords:
            task = Task.objects.create(
                scheduler_job=job,
                task_type=Task.TaskType.DATA_DUMP,
                entity_type=Task.EntityType.KEYWORD,
                entity_id=kw.id,
                entity_name=f"{kw.keyword} - {kw.pincode.pincode}",
                extra_context={
                    'keyword': kw.keyword,
                    'pincode': kw.pincode.pincode,
                    'keyword_id': kw.id,
                    'pincode_id': kw.pincode.id
                },
                status=Task.TaskStatus.PENDING,
            )
            created_tasks.append(task)
    
    return created_tasks


# ============================================================================
# JSON Build Operations (for Brand files)
# ============================================================================

def sync_files_table_for_brand(brand: Brand):
    """
    Ensure BrandJsonFile entries match configured templates for a brand.
    Creates missing entries and removes extras.
    """
    templates = getattr(settings, 'SCHEDULER_JSON_TEMPLATES', []) or []
    existing = BrandJsonFile.objects.filter(brand=brand, is_deleted=False)
    existing_templates = set(existing.values_list('template', flat=True))

    # Create missing entries
    for tpl in templates:
        if tpl not in existing_templates:
            try:
                BrandJsonFile.objects.create(brand=brand, template=tpl)
            except Exception:
                logger.exception(f'Failed to create BrandJsonFile for brand {brand.id} template {tpl}')

    # Remove entries not in config
    for e in existing:
        if e.template not in templates:
            try:
                e.delete()
            except Exception:
                logger.exception(f'Failed to delete extra BrandJsonFile {e.id}')


def resolve_json_build_tasks(job: SchedulerJob):
    """
    Create JSON_BUILD tasks based on scope for brands.
    
    Scope types:
    - GLOBAL: All active brands × all templates
    - BRAND: All templates for a specific brand ID (scope_id)
    - JSON: Retry a single file task (scope_id is Task ID)
    
    Returns:
        List of created Task objects
    """
    created_tasks = []
    templates = getattr(settings, 'SCHEDULER_JSON_TEMPLATES', [])

    if job.scope_type == SchedulerJob.ScopeType.GLOBAL:
        # All active brands × all templates
        brands = Brand.objects.filter(is_deleted=False, is_active=True)
        for brand in brands:
            sync_files_table_for_brand(brand)
            for tpl in templates:
                task = Task.objects.create(
                    scheduler_job=job,
                    task_type=Task.TaskType.JSON_BUILD,
                    entity_type=Task.EntityType.JSON_FILE,
                    entity_id=brand.id,
                    entity_name=tpl,
                    extra_context={'template': tpl, 'brand_id': brand.id},
                    status=Task.TaskStatus.PENDING,
                )
                created_tasks.append(task)
                
                # Ensure BrandJsonFile entry exists
                try:
                    BrandJsonFile.objects.get_or_create(brand_id=brand.id, template=tpl)
                except Exception:
                    logger.exception(f'Failed to ensure BrandJsonFile for {brand.id} {tpl}')

    elif job.scope_type == SchedulerJob.ScopeType.BRAND and job.scope_id:
        # All templates for specific brand
        brands = Brand.objects.filter(id=job.scope_id, is_deleted=False)
        for brand in brands:
            sync_files_table_for_brand(brand)
            for tpl in templates:
                task = Task.objects.create(
                    scheduler_job=job,
                    task_type=Task.TaskType.JSON_BUILD,
                    entity_type=Task.EntityType.JSON_FILE,
                    entity_id=brand.id,
                    entity_name=tpl,
                    extra_context={'template': tpl, 'brand_id': brand.id},
                    status=Task.TaskStatus.PENDING,
                )
                created_tasks.append(task)
                
                try:
                    BrandJsonFile.objects.get_or_create(brand_id=brand.id, template=tpl)
                except Exception:
                    logger.exception(f'Failed to ensure BrandJsonFile for {brand.id} {tpl}')

    elif job.scope_type == SchedulerJob.ScopeType.JSON and job.scope_id:
        # Retry single file task
        try:
            origin = Task.objects.get(id=job.scope_id)
            task = Task.objects.create(
                scheduler_job=job,
                task_type=Task.TaskType.JSON_BUILD,
                entity_type=Task.EntityType.JSON_FILE,
                entity_id=origin.entity_id,
                entity_name=origin.entity_name,
                extra_context=origin.extra_context,
                status=Task.TaskStatus.PENDING,
                retry_of_task=origin,
            )
            created_tasks.append(task)
        except Task.DoesNotExist:
            logger.error(f"Origin task {job.scope_id} not found for retry")

    return created_tasks


def resolve_scope_and_create_tasks(job: SchedulerJob):
    """
    Main dispatcher for creating tasks based on job's task_group and scope.
    
    Returns:
        List of all created Task objects
    """
    all_tasks = []
    
    # Handle DATA_DUMP tasks
    if job.task_group in (SchedulerJob.TaskGroup.DATA_DUMP, SchedulerJob.TaskGroup.BOTH):
        keyword_tasks = resolve_keyword_tasks(job)
        all_tasks.extend(keyword_tasks)
    
    # Handle JSON_BUILD tasks
    if job.task_group in (SchedulerJob.TaskGroup.JSON_BUILD, SchedulerJob.TaskGroup.BOTH):
        json_tasks = resolve_json_build_tasks(job)
        all_tasks.extend(json_tasks)
    
    return all_tasks
