import logging
from django.utils import timezone
from django.db import transaction
from celery import current_app
from .models import ActiveExecution, JsonFileTask, DataDumpTask, ExecutionHistory, TaskHistory

logger = logging.getLogger(__name__)

class ExecutionManager:
    @staticmethod
    def create_execution_from_scheduler(scheduler, user=None):
        """Legacy support for generic scheduler execution creation"""
        logger.info(f"Creating execution for scheduler: {scheduler.name}")
        execution = ActiveExecution.objects.create(
            scheduler=scheduler,
            execution_type=scheduler.type,
            configuration=scheduler.configuration,
            status='PENDING',
            created_by=user,
            started_at=timezone.now()
        )
        scheduler.last_run = timezone.now()
        scheduler.save(update_fields=['last_run'])
        return execution

    @staticmethod
    def stop_execution(execution):
        logger.info(f"Stopping execution: {execution.id}")
        if execution.celery_group_id:
            pass
        execution.status = 'STOPPED'
        execution.completed_at = timezone.now()
        execution.save(update_fields=['status', 'completed_at'])
        return execution

    @staticmethod
    def start_json_build(user, scope_type, scope_id, region_groups, scheduler=None):
        """
        region_groups example: {1: [{'template': 'A'}, {'template': 'B'}], 2: [{'template': 'A'}]}
        """
        # Upsert: Delete previous active execution for exactly same scope to keep UI clean
        ActiveExecution.objects.filter(
            execution_type='JSON_BUILD', 
            scope_type=scope_type, 
            scope_id=str(scope_id)
        ).exclude(status__in=['PENDING', 'RUNNING']).delete()

        total_files = sum(len(files) for files in region_groups.values())
        if total_files == 0:
            return None

        execution = ActiveExecution.objects.create(
            execution_type='JSON_BUILD',
            scope_type=scope_type,
            scope_id=str(scope_id),
            created_by=user,
            scheduler=scheduler,
            status='PENDING',
            total_tasks=total_files,
            started_at=timezone.now()
        )
        
        # Import here to avoid circular imports if needed, though we can import at top. 
        from experience_cloud.json_generator.models import RegionJsonFile

        # Create tasks in DB and dispatch to Celery per Region
        for region_id, files in region_groups.items():
            task_ids = []
            for file_data in files:
                task = JsonFileTask.objects.create(
                    execution=execution,
                    region_json_id=region_id,
                    metadata=file_data,
                    status='PENDING'
                )
                task_ids.append(task.id)
                
                if 'file_id' in file_data:
                    RegionJsonFile.objects.filter(id=file_data['file_id']).update(
                        task_id=str(task.id),
                        status='RUNNING',
                        error_message=None
                    )
            
            # The Magic Dispatch. No imports from json_generate needed.
            current_app.send_task(
                'experience_cloud.json_generator.tasks.process_region_batch',
                kwargs={
                    'execution_id': execution.id,
                    'region_id': region_id,
                    'file_task_ids': task_ids
                }
            )
            
        execution.status = 'RUNNING'
        execution.save(update_fields=['status'])
        return execution

    @staticmethod
    def start_data_dump(user, scope_type, scope_id, location_ids, scheduler=None):
        """Handles deduplication before creating tasks"""
        
        # Upsert: Delete previous active execution for exactly same scope
        ActiveExecution.objects.filter(
            execution_type='DATA_DUMP', 
            scope_type=scope_type, 
            scope_id=str(scope_id)
        ).exclude(status__in=['PENDING', 'RUNNING']).delete()

        # 1. Deduplication Check
        active_locations = set(DataDumpTask.objects.filter(
            metadata__location_id__in=location_ids,
            status__in=['PENDING', 'RUNNING']
        ).values_list('metadata__location_id', flat=True))
        
        locations_to_process = [loc for loc in location_ids if loc not in active_locations]
        
        if not locations_to_process:
            return None # Everything is already running
            
        execution = ActiveExecution.objects.create(
            execution_type='DATA_DUMP',
            scope_type=scope_type,
            scope_id=str(scope_id),
            created_by=user,
            scheduler=scheduler,
            status='RUNNING',
            total_tasks=len(locations_to_process),
            started_at=timezone.now()
        )
        
        # Import inside method
        from experience_cloud.market_data.models import ApiDump

        # 2. Create tasks and dispatch individually
        for loc_id in locations_to_process:
            task = DataDumpTask.objects.create(
                execution=execution,
                metadata={'location_id': loc_id},
                status='PENDING'
            )
            
            # Create matching ApiDump to track status per location
            ApiDump.objects.create(
                task_id=str(task.id),
                location_id=loc_id,
                status='RUNNING'
            )
            
            # Dispatch to the data_dump app worker
            current_app.send_task(
                'experience_cloud.market_data.tasks.process_location_dump',
                kwargs={'execution_id': execution.id, 'task_id': task.id, 'location_id': loc_id}
            )
            
        return execution

    @staticmethod
    def update_task_status(task_model, task_id, execution_id, status, error=None):
        """Called by the remote workers to update DB and check for completion"""
        task_model.objects.filter(id=task_id).update(
            status=status, 
            error_message=error,
            completed_at=timezone.now() if status in ['SUCCESS', 'FAILED'] else None
        )
        
        if status in ['SUCCESS', 'FAILED']:
            ExecutionManager._check_and_finalize(execution_id, task_model)

    @staticmethod
    def _check_and_finalize(execution_id, task_model):
        """Atomically checks if all tasks are done and moves to history immediately"""
        with transaction.atomic():
            execution = ActiveExecution.objects.select_for_update().get(id=execution_id)
            
            pending_count = task_model.objects.filter(
                execution=execution, 
                status__in=['PENDING', 'RUNNING']
            ).count()
            
            if pending_count == 0:
                # All tasks are done. Calculate if completely SUCCESS or some FAILED
                failed_count = task_model.objects.filter(
                    execution=execution, 
                    status='FAILED'
                ).count()
                
                execution.status = 'FAILED' if failed_count > 0 else 'SUCCESS'
                execution.completed_at = timezone.now()
                execution.completed_tasks = execution.total_tasks
                execution.failed_tasks = failed_count
                execution.save()

                # Immediate Archival to History
                history = ExecutionHistory.objects.create(
                    scheduler=execution.scheduler,
                    execution_type=execution.execution_type,
                    scope_type=execution.scope_type,
                    scope_id=execution.scope_id,
                    configuration=execution.configuration,
                    status=execution.status,
                    total_tasks=execution.total_tasks,
                    completed_tasks=execution.completed_tasks,
                    failed_tasks=execution.failed_tasks,
                    celery_group_id=execution.celery_group_id,
                    created_by=execution.created_by,
                    started_at=execution.started_at,
                    completed_at=execution.completed_at
                )

                # Duplicate Tasks
                tasks = task_model.objects.filter(execution=execution)
                history_tasks = []
                task_type_map = {JsonFileTask: 'JSON_BUILD', DataDumpTask: 'DATA_DUMP'}
                task_type = task_type_map.get(task_model, 'UNKNOWN')

                for t in tasks:
                    history_tasks.append(
                        TaskHistory(
                            execution=history,
                            task_type=task_type,
                            resource_id=t.metadata.get('location_id') or t.metadata.get('template') or t.region_json_id if hasattr(t, 'region_json_id') else None,
                            resource_metadata=t.metadata,
                            status=t.status,
                            retry_count=t.retry_count,
                            error_message=t.error_message,
                            celery_task_id=t.celery_task_id,
                            started_at=t.started_at,
                            completed_at=t.completed_at
                        )
                    )
                TaskHistory.objects.bulk_create(history_tasks)
                
                # Delete active execution (cascades to active tasks) to complete archival
                execution.delete()
