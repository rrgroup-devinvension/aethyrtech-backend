from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import JsonTemplateViewSet, RegionJsonFileViewSet, JsonGenerationStatsView

router = DefaultRouter()
router.register(r'templates', JsonTemplateViewSet, basename='json-template')
router.register(r'region-files', RegionJsonFileViewSet, basename='region-json-file')

urlpatterns = [
    path('stats/', JsonGenerationStatsView.as_view(), name='json-generation-stats'),
    path('', include(router.urls)),
]
