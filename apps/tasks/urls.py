"""
URL configuration for scheduler and tasks app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SchedulerViewSet,
    SchedulerJobViewSet,
    TaskViewSet,
    JsonBuilderBrandListView,
    DataDumpKeywordListView,
    DataDumpSyncAllView,
)

# Router for ViewSets
router = DefaultRouter()
router.register(r'schedulers', SchedulerViewSet, basename='scheduler')
router.register(r'jobs', SchedulerJobViewSet, basename='scheduler-job')
router.register(r'tasks', TaskViewSet, basename='task')

urlpatterns = [
    path('', include(router.urls)),
    path('data-dump/keywords/', DataDumpKeywordListView.as_view(), name='data-dump-keywords'),
    path('data-dump/sync-all/', DataDumpSyncAllView.as_view(), name='data-dump-sync-all'),
    path('json-builder/brands/', JsonBuilderBrandListView.as_view(), name='json-builder-brands'),
]
