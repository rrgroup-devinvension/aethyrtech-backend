from rest_framework.routers import DefaultRouter
from apps.brand.views import BrandViewSet

# Register only brand routes here. User routes are defined in apps.users.urls
router = DefaultRouter()
router.register(r"brands", BrandViewSet, basename="brand")

urlpatterns = router.urls
