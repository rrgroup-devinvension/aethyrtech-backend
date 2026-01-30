from celery import shared_task
from django.utils import timezone
from apps.scheduler.models import Task, SchedulerJob
from apps.scheduler.exceptions import SchedulerBaseException
from .data_dump.data_dump import perform_data_dump
from .json_builder.json_builder import perform_json_build
from .utility.service_utility import (
    update_entity_tracking_on_start,
    update_entity_tracking_on_complete,
    update_job_status
)
from django.db import transaction
import traceback
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def process_scheduler_job(self, job_id):
    try:
        job = SchedulerJob.objects.get(id=job_id)
    except SchedulerJob.DoesNotExist:
        logger.error(f"Job {job_id} not found")
        return {'status': 'error', 'message': 'Job not found'}
    tasks = job.tasks.filter(status=Task.TaskStatus.PENDING)
    for task in tasks:
        try:
            run_task.apply_async((task.id,))
        except Exception as e:
            logger.warning(f"Celery broker not available for task {task.id}, running synchronously: {e}")
    logger.info(f"Dispatched {tasks.count()} tasks for Job={job_id}")

@shared_task(bind=True, max_retries=2)
def run_task(self, task_id):
    try:
        task = Task.objects.select_related("scheduler_job").get(id=task_id)
    except Task.DoesNotExist:
        logger.error(f"Task {task_id} not found")
        return
    task.status = Task.TaskStatus.RUNNING
    task.started_at = timezone.now()
    task.celery_task_id = self.request.id
    task.save(update_fields=["status", "started_at", "celery_task_id"])
    update_entity_tracking_on_start(task)
    try:
        if task.task_type == Task.TaskType.DATA_DUMP:
            perform_data_dump(task)
        elif task.task_type == Task.TaskType.JSON_BUILD:
            perform_json_build(task)
        else:
            raise SchedulerBaseException("Invalid task type")
        with transaction.atomic():
            task.status = Task.TaskStatus.SUCCESS
            task.ended_at = timezone.now()
            task.error_message = None
            task.save(update_fields=["status","ended_at","error_message"])
            update_entity_tracking_on_complete(task, success=True)
            update_job_status(task.scheduler_job)
        logger.info(f"TASK SUCCESS {task.id}")
    except SchedulerBaseException as exc:
        debug_data = {"error": str(exc),"extra": exc.extra,"trace": traceback.format_exc()}
        with transaction.atomic():
            task.status = Task.TaskStatus.FAILED
            task.ended_at = timezone.now()
            task.error_message = exc.user_message
            ctx = task.extra_context or {}
            ctx["debug_error"] = debug_data
            task.extra_context = ctx
            task.save(update_fields=["status","ended_at","error_message","extra_context"])
            update_entity_tracking_on_complete(task, success=False, error_msg=exc.user_message)
            update_job_status(task.scheduler_job)
        logger.error(f"TASK FAILED [{exc.error_code}] {exc.user_message}")
        return
    except Exception as exc:
        debug_data = {"error": str(exc), "trace": traceback.format_exc()}
        with transaction.atomic():
            task.status = Task.TaskStatus.FAILED
            task.ended_at = timezone.now()
            task.error_message = "Internal system error"
            ctx = task.extra_context or {}
            ctx["debug_error"] = debug_data
            task.extra_context = ctx
            task.save(update_fields=["status","ended_at","error_message","extra_context"])
            update_entity_tracking_on_complete(task, success=False, error_msg="Internal system error")
            update_job_status(task.scheduler_job)
        logger.exception("Unhandled Celery crash")
        return

