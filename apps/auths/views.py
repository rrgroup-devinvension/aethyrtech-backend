from rest_framework import generics, status
from rest_framework.response import Response
from .serializers import LoginSerializer, ForgotPasswordSerializer, ResetPasswordSerializer
from .services import send_password_reset_email
from shared.response import api_response
from django.contrib.auth import get_user_model

User = get_user_model()

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .serializers import LoginSerializer, LogoutSerializer
from shared.response import api_response
from .models import LoginHistory
from django.utils import timezone
from rest_framework.permissions import AllowAny

User = get_user_model()

class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.get(email=request.data["email"])
        LoginHistory.objects.create(user=user, ip_address=request.META.get("REMOTE_ADDR"), user_agent=request.META.get("HTTP_USER_AGENT"))
        return Response(serializer.validated_data, status=status.HTTP_200_OK)

class LogoutView(generics.GenericAPIView):
    serializer_class = LogoutSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = RefreshToken(serializer.validated_data["refresh"])
        token.blacklist()
        # mark logout time
        LoginHistory.objects.filter(user=request.user, logged_out_at__isnull=True).update(logged_out_at=timezone.now())
        return api_response(message="Successfully logged out")



class ForgotPasswordView(generics.GenericAPIView):
    serializer_class = ForgotPasswordSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(email=serializer.validated_data["email"])
        send_password_reset_email(user)
        return api_response(message="Password reset link sent to email", data=None, status=200)


class ResetPasswordView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return api_response(message="Password has been reset successfully", data=None, status=200)

