from rest_framework.routers import DefaultRouter
from .views import BrandViewSet, UserBrandViewSet

router = DefaultRouter()
router.register(r"brands", BrandViewSet, basename="brand")
router.register(r"user-brands", UserBrandViewSet, basename="user-brand")

urlpatterns = router.urls
