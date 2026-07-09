from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PlatformViewSet

router = DefaultRouter()
router.register(r'platforms', PlatformViewSet, basename='platform')

urlpatterns = [
    path('', include(router.urls)),
]
