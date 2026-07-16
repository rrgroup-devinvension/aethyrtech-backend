from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import JsonTemplateViewSet, RegionJsonFileViewSet

router = DefaultRouter()
router.register(r'templates', JsonTemplateViewSet, basename='json-template')
router.register(r'region-files', RegionJsonFileViewSet, basename='region-json-file')

urlpatterns = [
    path('', include(router.urls)),
]