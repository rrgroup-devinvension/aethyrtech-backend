import logging
from django.utils import timezone
from .models import ActiveExecution

logger = logging.getLogger(__name__)

class ExecutionService:
    @staticmethod
    def create_execution(scheduler, user=None):
        """
        Create a new ActiveExecution from a Scheduler.
        """
        logger.info(f"Creating execution for scheduler: {scheduler.name}")
        
        # In a real scenario, this would likely trigger Celery tasks here
        execution = ActiveExecution.objects.create(
            scheduler=scheduler,
            execution_type=scheduler.type,
            configuration=scheduler.configuration,
            status='PENDING',
            created_by=user,
            started_at=timezone.now()
        )
        
        # Update scheduler's last_run
        scheduler.last_run = timezone.now()
        scheduler.save(update_fields=['last_run'])
        
        return execution

    @staticmethod
    def stop_execution(execution):
        """
        Stop an ActiveExecution.
        """
        logger.info(f"Stopping execution: {execution.id}")
        
        # Stop related celery tasks if any
        if execution.celery_group_id:
            pass # Celery group revoke logic would go here
            
        execution.status = 'STOPPED'
        execution.completed_at = timezone.now()
        execution.save(update_fields=['status', 'completed_at'])
        
        return execution
