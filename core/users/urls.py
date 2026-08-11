from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ChangePasswordView, ProfileView, RoleViewSet, UserViewSet, ContactUsView

router = DefaultRouter()
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'', UserViewSet, basename='user')

urlpatterns = [
    path('contact/', ContactUsView.as_view(), name='contact_us'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('', include(router.urls)),
]
