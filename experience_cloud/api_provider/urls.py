from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ApiProviderViewSet, ApiProviderAnalysisViewSet

router = DefaultRouter()
router.register(r'analysis', ApiProviderAnalysisViewSet, basename='api_provider_analysis')
router.register(r'', ApiProviderViewSet, basename='api_provider')

urlpatterns = [
    path('', include(router.urls)),
]
