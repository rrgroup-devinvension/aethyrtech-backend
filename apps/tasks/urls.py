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
from .views_gen_insights import (
    GenInsightsRegenerateView,
    GenInsightsBrandGraphView,
    GenInsightsRiskView,
    GenInsightsPositiveView,
    GenInsightsReviewsView,
    GenInsightsPlpView,
    GenInsightsPdpView,
    GenInsightsIncentiveView,
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
    path('json-builder/brands/', JsonBuilderBrandListView.as_view(), name='json-builder-brands'),
    path('gen-insights/regenerate', GenInsightsRegenerateView.as_view()),
    path('gen-insights/brand-graph', GenInsightsBrandGraphView.as_view()),
    path('gen-insights/risk', GenInsightsRiskView.as_view()),
    path('gen-insights/positive', GenInsightsPositiveView.as_view()),
    path('gen-insights/reviews', GenInsightsReviewsView.as_view()),
    path('gen-insights/plp', GenInsightsPlpView.as_view()),
    path('gen-insights/pdp', GenInsightsPdpView.as_view()),
    path('gen-insights/incentive', GenInsightsIncentiveView.as_view()),
]
