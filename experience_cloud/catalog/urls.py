from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PlatformViewSet, LocationViewSet, KeywordViewSet

router = DefaultRouter()
router.register(r'platforms', PlatformViewSet, basename='catalog-platform')
router.register(r'locations', LocationViewSet, basename='catalog-location')
router.register(r'keywords', KeywordViewSet, basename='catalog-keyword')

urlpatterns = [
    path('', include(router.urls)),
]