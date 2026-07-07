
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

def ensure_keyword_pincodes_bulk(pairs):
    """
    Ensure KeywordPincodes exist for a list of (keyword, pincode) tuples.
    Returns a dictionary mapping (keyword, pincode) to KeywordPincode object.
    """
    if not pairs:
        return {}
        
    keywords = set([p[0] for p in pairs])
    pincodes = set([p[1] for p in pairs])
    
    existing = KeywordPincode.objects.filter(keyword__in=keywords, pincode__in=pincodes)
    existing_map = {(kp.keyword, kp.pincode): kp for kp in existing}
    
    to_create = []
    to_update = []
    
    for kw, pin in pairs:
        if (kw, pin) in existing_map:
            kp = existing_map[(kw, pin)]
            if getattr(kp, 'is_deleted', False):
                kp.is_deleted = False
                to_update.append(kp)
        else:
            to_create.append(KeywordPincode(keyword=kw, pincode=pin))
            
    if to_update:
        KeywordPincode.objects.bulk_update(to_update, ['is_deleted'])
    if to_create:
        created = KeywordPincode.objects.bulk_create(to_create)
        for kp in created:
            existing_map[(kp.keyword, kp.pincode)] = kp
            
    return existing_map

def update_job_status(job):

    with transaction.atomic():

        job = SchedulerJob.objects.select_for_update().get(id=job.id)

        has_running = job.tasks.filter(status=Task.TaskStatus.RUNNING).exists()
        has_pending = job.tasks.filter(status=Task.TaskStatus.PENDING).exists()
        has_success = job.tasks.filter(status=Task.TaskStatus.SUCCESS).exists()
        has_failed = job.tasks.filter(status=Task.TaskStatus.FAILED).exists()

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
    
    # Bulk update entity tracking
    kp_updates = []
    bj_updates = []
    
    bj_brand_ids = [t.entity_id for t in saved_tasks if t.task_type == Task.TaskType.JSON_BUILD and t.entity_type == Task.EntityType.JSON_FILE]
    bj_task_map = {}
    if bj_brand_ids:
        bj_task_map = {b.brand_id: b for b in BrandJsonTask.objects.filter(brand_id__in=bj_brand_ids)}
        
    for task in saved_tasks:
        if task.task_type == Task.TaskType.DATA_DUMP and task.entity_type == Task.EntityType.KEYWORD_PINCODE:
            kp_updates.append(KeywordPincode(id=task.entity_id, last_running_task=task))
        elif task.task_type == Task.TaskType.JSON_BUILD and task.entity_type == Task.EntityType.JSON_FILE:
            if task.entity_id and task.entity_id in bj_task_map:
                bj = bj_task_map[task.entity_id]
                bj.last_running_task = task
                bj_updates.append(bj)
                
    if kp_updates:
        KeywordPincode.objects.bulk_update(kp_updates, ['last_running_task'])
    if bj_updates:
        BrandJsonTask.objects.bulk_update(bj_updates, ['last_running_task'])

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
