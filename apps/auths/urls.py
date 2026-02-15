from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LoginView, 
    LogoutView, 
    RefreshView,
    ForgotPasswordView,
    VerifyOTPView,
    ResetPasswordView
)


router = DefaultRouter()

urlpatterns = [
    path("", include(router.urls)),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify-otp"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
]