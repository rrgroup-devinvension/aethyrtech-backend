from celery import shared_task
from django.utils import timezone
from .models import Task, SchedulerJob, Scheduler
from django.db import transaction
import traceback
from . import services
from .models import BrandJsonFile


@shared_task(bind=True)
def run_task(self, task_id: int):
    """Entrypoint Celery task that runs a single Task record."""
    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return {'status': 'missing'}

    task.status = Task.TaskStatus.RUNNING
    task.started_at = timezone.now()
    task.save(update_fields=['status', 'started_at'])

    try:
        # Dispatch based on task_type
        if task.task_type == Task.TaskType.DATA_DUMP:
            _perform_data_dump(task)
        elif task.task_type == Task.TaskType.JSON_BUILD:
            _perform_json_build(task)
        else:
            raise RuntimeError('Unknown task type')

        task.status = Task.TaskStatus.SUCCESS
        task.ended_at = timezone.now()
        task.save(update_fields=['status', 'ended_at'])
        return {'status': 'success'}

    except Exception as exc:
        task.status = Task.TaskStatus.FAILED
        task.ended_at = timezone.now()
        task.error_message = traceback.format_exc()
        task.save(update_fields=['status', 'ended_at', 'error_message'])
        # Update BrandJsonFile to record error (do not change existing file_path)
        try:
            tpl = (task.extra_context or {}).get('template')
            if tpl and task.entity_id:
                bobj = BrandJsonFile.objects.filter(brand_id=task.entity_id, template=tpl).first()
                if bobj:
                    bobj.error_message = task.error_message
                    bobj.last_synced = timezone.now()
                    bobj.save(update_fields=['error_message', 'last_synced'])
        except Exception:
            # do not mask original exception path
            logger = __import__('logging').getLogger(__name__)
            logger.exception('Failed to update BrandJsonFile on task failure %s', task.id)
        return {'status': 'failed', 'error': str(exc)}


def _perform_data_dump(task: Task):
    """Placeholder logic to dump data from API for the given entity.
    Replace with actual implementation.
    """
    import requests
    from django.conf import settings
    # Example: call external API using configured base
    base = getattr(settings, 'SCHEDULER_EXTERNAL_API_BASE', '')
    api_key = getattr(settings, 'SCHEDULER_EXTERNAL_API_KEY', None)
    payload = {}
    try:
        if base:
            # construct endpoint; this is a placeholder, expects task.extra_context to have endpoint/path
            path = (task.extra_context or {}).get('endpoint', '')
            url = base.rstrip('/') + '/' + path.lstrip('/')
            headers = {}
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            payload = resp.json()
        else:
            # no external api configured; put placeholder data
            payload = {'dummy': True, 'entity': task.entity_name}

        # optionally save payload to MEDIA or DB; reuse build_and_save_json_for_task for now
        services.build_and_save_json_for_task(task, payload)
    except Exception:
        raise


def _perform_json_build(task: Task):
    """Placeholder logic to build JSON from database.
    Replace with actual implementation.
    """
    # Build a simple JSON containing metadata and optionally aggregated data
    payload = {
        'entity_name': task.entity_name,
        'entity_id': task.entity_id,
        'generated_at': timezone.now().isoformat(),
        'extra_context': task.extra_context or {},
    }

    # In future: build actual data by querying DB
    services.build_and_save_json_for_task(task, payload)


@shared_task(bind=True)
def process_scheduler_job(self, scheduler_job_id: int):
    """High level task to process a SchedulerJob: resolve scope, create tasks and push them to celery."""
    try:
        job = SchedulerJob.objects.get(id=scheduler_job_id)
    except SchedulerJob.DoesNotExist:
        return {'status': 'missing'}

    job.started_at = timezone.now()
    job.status = SchedulerJob.JobStatus.RUNNING
    job.save(update_fields=['started_at', 'status'])

    # Resolve scope and create tasks
    # Resolve scope and create tasks using services
    tasks_to_enqueue = services.resolve_scope_and_create_tasks(job)

    # push tasks to celery
    for t in tasks_to_enqueue:
        run_task.apply_async((t.id,))

    # mark job as enqueued/running; final status will be computed by auto_update_job_status
    job.status = SchedulerJob.JobStatus.RUNNING
    job.started_at = job.started_at or timezone.now()
    job.save(update_fields=['status', 'started_at'])

    return {'status': 'enqueued', 'tasks': [t.id for t in tasks_to_enqueue]}


@shared_task(bind=True)
def trigger_scheduler(self, scheduler_id: int):
    """Called by django-celery-beat PeriodicTask to trigger a scheduler run."""
    from .services import create_scheduler_job
    # Create a SchedulerJob with task group based on Scheduler.type
    try:
        sched = Scheduler.objects.get(id=scheduler_id)
    except Scheduler.DoesNotExist:
        return {'status': 'missing_scheduler'}

    tg = SchedulerJob.TaskGroup.BOTH
    if sched.type == 'JSON_BUILD':
        tg = SchedulerJob.TaskGroup.JSON_BUILD
    elif sched.type == 'KEYWORD_SYNC':
        tg = SchedulerJob.TaskGroup.DATA_DUMP

    job = create_scheduler_job(scheduler_id=scheduler_id, triggered_by='SYSTEM', scope_type='GLOBAL', scope_id=None, task_group=tg)
    return {'status': 'created', 'job_id': job.id}
