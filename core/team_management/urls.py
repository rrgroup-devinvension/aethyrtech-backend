from rest_framework.routers import DefaultRouter
from .views import TeamMemberViewSet

app_name = 'team_management'

router = DefaultRouter()
router.register(r'members', TeamMemberViewSet, basename='teammember')

urlpatterns = router.urls
