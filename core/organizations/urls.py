from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrganizationViewSet, BrandViewSet, CompetitorViewSet, RegionViewSet

router = DefaultRouter()
router.register(r'organizations', OrganizationViewSet, basename='organization')
router.register(r'brands', BrandViewSet, basename='brand')
router.register(r'regions', RegionViewSet, basename='region')
router.register(r'competitors', CompetitorViewSet, basename='competitor')

urlpatterns = [
    path('', include(router.urls)),
]
