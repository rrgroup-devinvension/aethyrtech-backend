from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ApiProviderViewSet

router = DefaultRouter()
router.register(r'', ApiProviderViewSet, basename='api_provider')

urlpatterns = [
    path('', include(router.urls)),
]
