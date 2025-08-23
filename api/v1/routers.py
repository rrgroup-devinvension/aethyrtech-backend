from rest_framework.routers import DefaultRouter
from apps.brand.views import BrandViewSet
from apps.users.views import UserViewSet

router = DefaultRouter()
router.register(r"brands", BrandViewSet, basename="brand")
router.register(r"users", UserViewSet, basename="user")

urlpatterns = router.urls
