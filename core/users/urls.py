from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, ProfileView, ChangePasswordView

router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')

urlpatterns = [
    path('profile/', ProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('', include(router.urls)),
]
