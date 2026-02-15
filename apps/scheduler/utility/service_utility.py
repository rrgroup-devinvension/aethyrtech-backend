
from django.utils import timezone
from apps.scheduler.models import Task, KeywordPincode, BrandJsonTask, BrandJsonFile, SchedulerJob
import logging
from django.db import transaction

logger = logging.getLogger(__name__)

# ============================================================================
# Entity Tracking
# ============================================================================

def ensure_brand_json_files(brand, templates):
    """Ensure BrandJsonFile entries exist for all templates."""
    BrandJsonTask.objects.get_or_create(brand=brand)
    for template in templates:
        BrandJsonFile.objects.get_or_create(brand=brand, template=template)

def ensure_keyword_pincode_single(keyword, category_pincode):
    """Ensure a single KeywordPincode exists for given keyword and category_pincode."""
    # Accept either CategoryKeyword/CategoryPincode objects or plain strings.
    if hasattr(keyword, 'keyword'):
        keyword_text = keyword.keyword
    else:
        keyword_text = str(keyword)

    if hasattr(category_pincode, 'pincode'):
        pincode_text = category_pincode.pincode
    else:
        pincode_text = str(category_pincode)

    kp = KeywordPincode.objects.filter(keyword=keyword_text, pincode=pincode_text).first()
    if kp:
        if getattr(kp, 'is_deleted', False):
            kp.is_deleted = False
            kp.save(update_fields=['is_deleted'])
    else:
        kp = KeywordPincode.objects.create(keyword=keyword_text, pincode=pincode_text)
    return kp

def update_job_status(job):

    with transaction.atomic():

        job = SchedulerJob.objects.select_for_update().get(id=job.id)

        tasks = job.tasks.all()

        statuses = list(tasks.values_list('status', flat=True))

        has_running = Task.TaskStatus.RUNNING in statuses
        has_pending = Task.TaskStatus.PENDING in statuses
        has_success = Task.TaskStatus.SUCCESS in statuses
        has_failed = Task.TaskStatus.FAILED in statuses

        if has_running or has_pending:
            job.status = SchedulerJob.JobStatus.RUNNING
            job.save(update_fields=['status'])
            return
        job.ended_at = timezone.now()
        if has_success and has_failed:
            job.status = SchedulerJob.JobStatus.PARTIAL
        elif has_failed:
            job.status = SchedulerJob.JobStatus.FAILED
        elif has_success:
            job.status = SchedulerJob.JobStatus.SUCCESS
        job.save(update_fields=['status', 'ended_at'])

def bulk_create_tasks(job, tasks_config):
    """Bulk create Task instances."""
    task_objects = [
        Task(
            scheduler_job=job,
            task_type=config['task_type'],
            entity_type=config['entity_type'],
            entity_id=config['entity_id'],
            entity_name=config['entity_name'],
            extra_context=config.get('extra_context'),
            status=Task.TaskStatus.PENDING,
        )
        for config in tasks_config
    ]
    if not task_objects:
        return
    Task.objects.bulk_create(task_objects)
    logger.info(f"Created {len(task_objects)} tasks for job {job.id}")

    saved_tasks = Task.objects.filter(scheduler_job=job)
    for task in saved_tasks:
        update_entity_tracking_on_start(task)

def update_entity_tracking_on_start(task):
    """Update entity's last_running_task when task starts."""
    if task.task_type == Task.TaskType.DATA_DUMP and task.entity_type == Task.EntityType.KEYWORD_PINCODE:
        try:
            kp = KeywordPincode.objects.get(id=task.entity_id)
            kp.last_running_task = task
            kp.save(update_fields=['last_running_task'])
        except KeywordPincode.DoesNotExist:
            logger.warning(f"KeywordPincode {task.entity_id} not found for task {task.id}")
    
    elif task.task_type == Task.TaskType.JSON_BUILD and task.entity_type == Task.EntityType.JSON_FILE:
        try:
            if task.entity_id:
                brand_json = BrandJsonTask.objects.get(brand_id=task.entity_id)
                brand_json.last_running_task = task
                brand_json.save(update_fields=['last_running_task'])
        except BrandJsonTask.DoesNotExist:
            logger.warning(f"BrandJsonTask for brand {task.entity_id} not found")


def update_entity_tracking_on_complete(task, success=True, error_msg=None):
    if task.task_type == Task.TaskType.DATA_DUMP and task.entity_type == Task.EntityType.KEYWORD_PINCODE:
        try:
            kp = KeywordPincode.objects.get(id=task.entity_id)
            if success:
                kp.last_completed_task = task
                kp.last_synced = timezone.now()
                kp.error_message = None
            else:
                kp.last_completed_task = None
                kp.last_synced = None
                kp.error_message = error_msg
            kp.save(update_fields=[
                "last_completed_task",
                "last_synced",
                "error_message"
            ])
        except KeywordPincode.DoesNotExist:
            logger.warning(f"KeywordPincode {task.entity_id} not found")

    elif task.task_type == Task.TaskType.JSON_BUILD and task.entity_type == Task.EntityType.JSON_FILE:
        try:
            brand_json = BrandJsonTask.objects.get(brand_id=task.entity_id)
            if success:
                brand_json.last_completed_task = task
                brand_json.last_synced = timezone.now()
                brand_json.error_message = None
                brand_json.save(update_fields=[
                    "last_completed_task",
                    "last_synced",
                    "error_message",
                ])
            else:
                brand_json.last_completed_task = None
                brand_json.last_synced = None
                brand_json.error_message = error_msg
                brand_json.save(update_fields=[
                    "last_completed_task",
                    "last_synced",
                    "error_message"
                ])
        except BrandJsonTask.DoesNotExist:
            logger.warning(f"BrandJsonTask not found → brand={task.entity_id}")
