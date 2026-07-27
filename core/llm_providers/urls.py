from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LLMProviderViewSet, LLMAnalysisViewSet

router = DefaultRouter()
router.register(r'providers', LLMProviderViewSet, basename='llm_provider')
router.register(r'analysis', LLMAnalysisViewSet, basename='llm_analysis')

urlpatterns = [
    path('', include(router.urls)),
]