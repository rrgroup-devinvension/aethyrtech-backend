from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import LLMAnalysisViewSet, LLMProviderViewSet

router = DefaultRouter()
router.register(r'providers', LLMProviderViewSet, basename='llm_provider')
router.register(r'analysis', LLMAnalysisViewSet, basename='llm_analysis')

urlpatterns = [
    path('', include(router.urls)),
]
