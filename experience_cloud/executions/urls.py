from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SchedulerViewSet, ActiveExecutionViewSet, ExecutionHistoryViewSet,
    DataDumpTaskViewSet, JsonFileTaskViewSet, TaskHistoryViewSet
)

router = DefaultRouter()
router.register(r'schedulers', SchedulerViewSet)
router.register(r'active-executions', ActiveExecutionViewSet)
router.register(r'execution-history', ExecutionHistoryViewSet)
router.register(r'data-dump-tasks', DataDumpTaskViewSet)
router.register(r'json-file-tasks', JsonFileTaskViewSet)
router.register(r'task-history', TaskHistoryViewSet)

urlpatterns = [
    path('', include(router.urls)),
]