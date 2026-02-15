from rest_framework.routers import DefaultRouter

# Brand and Organization routes are defined in apps.brand.urls
# User routes are defined in apps.users.urls
# Category routes are defined in apps.category.urls
router = DefaultRouter()

urlpatterns = router.urls
