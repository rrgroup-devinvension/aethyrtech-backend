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
        
        # Stop all child tasks so Celery workers abort them
        if execution.execution_type == 'DATA_DUMP':
            tasks_qs = DataDumpTask.objects.filter(execution=execution, status__in=['PENDING', 'RUNNING'])
            celery_task_ids = list(tasks_qs.exclude(celery_task_id__isnull=True).values_list('celery_task_id', flat=True))
            tasks_qs.update(status='STOPPED', error_message='Execution manually stopped')
            
            from experience_cloud.market_data.models import ApiDump
            task_ids = DataDumpTask.objects.filter(execution=execution).values_list('id', flat=True)
            ApiDump.objects.filter(task_id__in=[str(tid) for tid in task_ids], status__in=['PENDING', 'RUNNING']).update(status='STOPPED', error_message='Execution manually stopped')
            task_model = DataDumpTask
        else:
            tasks_qs = JsonFileTask.objects.filter(execution=execution, status__in=['PENDING', 'RUNNING'])
            celery_task_ids = list(tasks_qs.exclude(celery_task_id__isnull=True).values_list('celery_task_id', flat=True))
            tasks_qs.update(status='STOPPED', error_message='Execution manually stopped')
            
            from experience_cloud.json_generator.models import RegionJsonFile
            task_ids = JsonFileTask.objects.filter(execution=execution).values_list('id', flat=True)
            RegionJsonFile.objects.filter(task_id__in=[str(tid) for tid in task_ids], status__in=['PENDING', 'RUNNING']).update(status='STOPPED', error_message='Execution manually stopped')
            task_model = JsonFileTask

        # Ruthlessly kill tasks in celery broker
        if celery_task_ids:
            for c_task_id in celery_task_ids:
                if c_task_id:
                    current_app.control.revoke(c_task_id, terminate=True, signal='SIGTERM')

        stopped_count = len(celery_task_ids)
        
        # Archive to history
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
            stopped_tasks=stopped_count,
            celery_group_id=execution.celery_group_id,
            created_by=execution.created_by,
            started_at=execution.started_at,
            completed_at=execution.completed_at
        )

        tasks = task_model.objects.filter(execution=execution)
        history_tasks = []
        task_type = 'DATA_DUMP' if execution.execution_type == 'DATA_DUMP' else 'JSON_BUILD'
        
        for t in tasks:
            history_tasks.append(
                TaskHistory(
                    execution=history,
                    task_type=task_type,
                    resource_id=t.metadata.get('location_id') or t.metadata.get('template') or (t.region_json_id if hasattr(t, 'region_json_id') else None),
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
        execution.delete()
        
        return history

    @staticmethod
    def start_json_build(user, scope_type, scope_id, region_groups, scheduler=None, scope_name=None):
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
            scope_name=scope_name,
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
            async_result = current_app.send_task(
                'experience_cloud.json_generator.tasks.process_region_batch',
                kwargs={
                    'execution_id': execution.id,
                    'region_id': region_id,
                    'file_task_ids': task_ids
                }
            )
            # Update the parent tasks with celery ID (if applicable to JSON tasks)
            JsonFileTask.objects.filter(id__in=task_ids).update(celery_task_id=async_result.id)
            
        execution.status = 'RUNNING'
        execution.save(update_fields=['status'])
        return execution

    @staticmethod
    def start_data_dump(user, scope_type, scope_id, task_pairs, scheduler=None, scope_name=None):
        """Handles deduplication before creating tasks using keyword_id and location_id"""
        
        # Upsert: Delete previous active execution for exactly same scope
        ActiveExecution.objects.filter(
            execution_type='DATA_DUMP', 
            scope_type=scope_type, 
            scope_id=str(scope_id)
        ).exclude(status__in=['PENDING', 'RUNNING']).delete()

        # 1. Deduplication Check based on (keyword_id, location_id)
        active_tasks = DataDumpTask.objects.filter(
            status__in=['PENDING', 'RUNNING']
        ).values_list('metadata__keyword_id', 'metadata__location_id')
        
        # active_tasks returns string values from JSONField on some DBs, so normalize
        active_set = {(str(kw), str(loc)) for kw, loc in active_tasks if kw and loc}
        
        tasks_to_process = []
        for pair in task_pairs:
            kw_id = str(pair['keyword_id'])
            loc_id = str(pair['location_id'])
            if (kw_id, loc_id) not in active_set:
                tasks_to_process.append(pair)
        
        if not tasks_to_process:
            return None # Everything is already running
            
        execution = ActiveExecution.objects.create(
            execution_type='DATA_DUMP',
            scope_type=scope_type,
            scope_id=str(scope_id),
            scope_name=scope_name,
            created_by=user,
            scheduler=scheduler,
            status='RUNNING',
            total_tasks=len(tasks_to_process),
            started_at=timezone.now()
        )
        
        # Import inside method
        from experience_cloud.market_data.models import ApiDump
        from experience_cloud.catalog.models import Keyword, Location

        # Pre-fetch for performance to avoid N+1 queries
        keyword_ids = {p['keyword_id'] for p in tasks_to_process}
        location_ids = {p['location_id'] for p in tasks_to_process}
        
        keywords = {k.id: k for k in Keyword.objects.filter(id__in=keyword_ids)}
        locations = {l.id: l for l in Location.objects.filter(id__in=location_ids)}

        # 2. Create tasks and dispatch individually
        for pair in tasks_to_process:
            kw_id = pair['keyword_id']
            loc_id = pair['location_id']
            
            # We want to format the resource name as 'Keyword / Location'
            kw = keywords.get(kw_id)
            loc = locations.get(loc_id)
            
            kw_name = kw.keyword if kw else str(kw_id)
            loc_name = str(loc.pincode) if (loc and loc.pincode) else (str(loc.address) if loc else str(loc_id))
            resource_name = f"{kw_name} / {loc_name}"

            task = DataDumpTask.objects.create(
                execution=execution,
                metadata={'keyword_id': kw_id, 'location_id': loc_id, 'resource_name': resource_name},
                status='PENDING'
            )
            
            # Create matching ApiDump to track status per keyword+location
            ApiDump.objects.create(
                task_id=str(task.id),
                keyword_id=kw_id,
                location_id=loc_id,
                platform_id=pair.get('platform_id'),
                api_provider_id=pair.get('api_provider_id'),
                status='PENDING'
            )
            
            # Dispatch to the data_dump app worker
            async_result = current_app.send_task(
                'experience_cloud.market_data.tasks.process_location_dump',
                kwargs={'execution_id': execution.id, 'task_id': task.id, 'keyword_id': kw_id, 'location_id': loc_id}
            )
            task.celery_task_id = async_result.id
            task.save(update_fields=['celery_task_id'])
            
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
            with transaction.atomic():
                execution = ActiveExecution.objects.select_for_update().get(id=execution_id)
                
                # Increment completed_tasks for real-time tracking
                execution.completed_tasks += 1
                if status == 'FAILED':
                    execution.failed_tasks += 1
                execution.save(update_fields=['completed_tasks', 'failed_tasks'])
            
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
                # All tasks are done. Calculate if completely SUCCESS or some FAILED or STOPPED
                failed_count = task_model.objects.filter(
                    execution=execution, 
                    status='FAILED'
                ).count()
                
                stopped_count = task_model.objects.filter(
                    execution=execution, 
                    status='STOPPED'
                ).count()
                
                if stopped_count > 0:
                    execution.status = 'STOPPED'
                elif failed_count > 0:
                    execution.status = 'FAILED'
                else:
                    execution.status = 'SUCCESS'
                    
                execution.completed_at = timezone.now()
                # Completed tasks are those that actually succeeded
                success_count = task_model.objects.filter(execution=execution, status='SUCCESS').count()
                execution.completed_tasks = success_count
                execution.failed_tasks = failed_count
                execution.stopped_tasks = stopped_count
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
                    stopped_tasks=execution.stopped_tasks,
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
