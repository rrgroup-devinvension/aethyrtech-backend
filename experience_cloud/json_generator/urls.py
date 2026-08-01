from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DebugRunJsonBuildView, JsonGenerationStatsView, JsonTemplateViewSet, RegionJsonFileViewSet

router = DefaultRouter()
router.register(r'templates', JsonTemplateViewSet, basename='json-template')
router.register(r'region-files', RegionJsonFileViewSet, basename='region-json-file')

urlpatterns = [
    path('debug-run/', DebugRunJsonBuildView.as_view(), name='debug-run'),
    path('stats/', JsonGenerationStatsView.as_view(), name='json-generation-stats'),
    path('', include(router.urls)),
]
