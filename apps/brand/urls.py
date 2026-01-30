from rest_framework.routers import DefaultRouter
from .views import BrandViewSet, OrganizationViewSet, CompetitorViewSet

router = DefaultRouter()
router.register(r"brands", BrandViewSet, basename="brand")
router.register(r"organizations", OrganizationViewSet, basename="organization")
router.register(r"competitors", CompetitorViewSet, basename="competitor")

urlpatterns = router.urls
