from django.contrib import admin
from .models import Scheduler, SchedulerJob, Task


@admin.register(Scheduler)
class SchedulerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'type', 'trigger_type', 'status', 'last_run_at', 'next_run_at')
    search_fields = ('name',)
    list_filter = ('type', 'trigger_type', 'status')


@admin.register(SchedulerJob)
class SchedulerJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'scheduler', 'triggered_by', 'scope_type', 'task_group', 'status', 'started_at', 'ended_at')
    list_filter = ('status', 'task_group', 'scope_type')


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'scheduler_job', 'task_type', 'entity_type', 'entity_name', 'status', 'started_at', 'ended_at')
    list_filter = ('status', 'task_type', 'entity_type')
    search_fields = ('entity_name',)
