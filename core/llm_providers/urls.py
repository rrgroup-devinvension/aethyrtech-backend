from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LLMProviderViewSet

router = DefaultRouter()
router.register(r'providers', LLMProviderViewSet, basename='llm_provider')

urlpatterns = [
    path('', include(router.urls)),
]