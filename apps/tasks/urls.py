from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    JsonsListView,
    BrandFilesView,
    BrandSyncView,
    FileSyncView,
    JsonSyncAllView,
    JsonJobStatusView,
    SchedulerViewSet,
    SchedulerJobViewSet,
    TaskViewSet,
    SchedulerJobListView,
    StopSchedulerJobView,
    TaskListView,
    DataDumpListView,
    KeywordSyncAllView,
    KeywordSyncView,
    DataDumpJobStatusView,
    StopTaskView,
)
from apps.scheduler.viewsets import PincodeViewSet, KeywordViewSet

router = DefaultRouter()
router.register(r'schedulers', SchedulerViewSet, basename='scheduler')
router.register(r'jobs', SchedulerJobViewSet, basename='schedulerjob')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'pincodes', PincodeViewSet, basename='pincode')
router.register(r'keywords', KeywordViewSet, basename='keyword')

urlpatterns = [
    path('', include(router.urls)),
    # JSON Builder endpoints
    path('jsons/', JsonsListView.as_view(), name='jsons-list'),
    path('jsons/sync-all/', JsonSyncAllView.as_view(), name='jsons-sync-all'),
    path('jsons/job-status/', JsonJobStatusView.as_view(), name='jsons-job-status'),
    path('jsons/<int:brand_id>/sync/', BrandSyncView.as_view(), name='jsons-sync-brand'),
    path('jsons/<int:brand_id>/files/', BrandFilesView.as_view(), name='jsons-brand-files'),
    path('jsons/files/<int:file_id>/sync/', FileSyncView.as_view(), name='jsons-file-sync'),
    # Data Dump endpoints
    path('data-dump/', DataDumpListView.as_view(), name='data-dump-list'),
    path('data-dump/sync-all/', KeywordSyncAllView.as_view(), name='data-dump-sync-all'),
    path('data-dump/job-status/', DataDumpJobStatusView.as_view(), name='data-dump-job-status'),
    path('data-dump/<int:keyword_id>/sync/', KeywordSyncView.as_view(), name='data-dump-sync-keyword'),
    # Job and Task management
    path('scheduler-jobs/', SchedulerJobListView.as_view(), name='scheduler-jobs-list'),
    path('scheduler-jobs/<int:job_id>/stop/', StopSchedulerJobView.as_view(), name='scheduler-job-stop'),
    path('all-tasks/', TaskListView.as_view(), name='all-tasks-list'),
    path('all-tasks/<int:task_id>/stop/', StopTaskView.as_view(), name='task-stop'),
]
