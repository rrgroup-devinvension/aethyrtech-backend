from .serializers import (
    LoginSerializer, 
    LogoutSerializer, 
    RefreshSerializer,
    ForgotPasswordSerializer,
    VerifyOTPSerializer,
    ResetPasswordSerializer
)
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .models import LoginHistory, PasswordResetOTP
from django.utils import timezone
from rest_framework.permissions import AllowAny
from django.core.mail import send_mail
from django.conf import settings

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

class RefreshView(generics.GenericAPIView):
    serializer_class = RefreshSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
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
        return Response({"message": "Successfully logged out"}, status=status.HTTP_200_OK)


class ForgotPasswordView(generics.GenericAPIView):
    """Send OTP to user's email for password reset"""
    serializer_class = ForgotPasswordSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        user = User.objects.get(email=email, is_active=True, is_deleted=False)
        
        # Create OTP
        otp_instance = PasswordResetOTP.create_otp(user)
        
        # Send email with OTP
        try:
            send_mail(
                subject='Password Reset OTP - AethyrTech',
                message=f'Your OTP for password reset is: {otp_instance.otp}\n\nThis OTP will expire in 10 minutes.\n\nIf you did not request this, please ignore this email.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as e:
            return Response(
                {"detail": "Failed to send OTP email. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response(
            {"detail": "OTP has been sent to your email address"},
            status=status.HTTP_200_OK
        )


class VerifyOTPView(generics.GenericAPIView):
    """Verify OTP without resetting password"""
    serializer_class = VerifyOTPSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        
        try:
            user = User.objects.get(email=email, is_active=True, is_deleted=False)
        except User.DoesNotExist:
            return Response(
                {"detail": "Invalid email address"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the latest unused OTP
        try:
            otp_instance = PasswordResetOTP.objects.filter(
                user=user,
                otp=otp,
                is_used=False
            ).latest('created_at')
        except PasswordResetOTP.DoesNotExist:
            return Response(
                {"detail": "Invalid OTP"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not otp_instance.is_valid():
            return Response(
                {"detail": "OTP has expired or already been used"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(
            {"detail": "OTP verified successfully"},
            status=status.HTTP_200_OK
        )


class ResetPasswordView(generics.GenericAPIView):
    """Reset password using OTP"""
    serializer_class = ResetPasswordSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']
        
        try:
            user = User.objects.get(email=email, is_active=True, is_deleted=False)
        except User.DoesNotExist:
            return Response(
                {"detail": "Invalid email address"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the latest unused OTP
        try:
            otp_instance = PasswordResetOTP.objects.filter(
                user=user,
                otp=otp,
                is_used=False
            ).latest('created_at')
        except PasswordResetOTP.DoesNotExist:
            return Response(
                {"detail": "Invalid OTP"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not otp_instance.is_valid():
            return Response(
                {"detail": "OTP has expired or already been used"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reset password
        user.set_password(new_password)
        user.save()
        
        # Mark OTP as used
        otp_instance.is_used = True
        otp_instance.save()
        
        return Response(
            {"detail": "Password has been reset successfully"},
            status=status.HTTP_200_OK
        )
