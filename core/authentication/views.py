import logging
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .serializers import (
    LoginSerializer, 
    LogoutSerializer, 
    RefreshSerializer,
    ForgotPasswordSerializer,
    VerifyOTPSerializer,
    ResetPasswordSerializer
)
from .services import AuthenticationService

logger = logging.getLogger(__name__)
User = get_user_model()

class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        summary="User Login",
        description="Authenticate user and return access & refresh tokens.",
        responses={200: LoginSerializer, 400: OpenApiResponse(description="Invalid credentials")}
    )
    def post(self, request):
        logger.info("Login attempt received.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = User.objects.get(email=request.data["email"])
        ip_address = request.META.get("REMOTE_ADDR")
        user_agent = request.META.get("HTTP_USER_AGENT")
        
        AuthenticationService.record_login(user, ip_address, user_agent)
        
        return Response(serializer.validated_data, status=status.HTTP_200_OK)

class RefreshView(generics.GenericAPIView):
    serializer_class = RefreshSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Refresh Token",
        description="Get a new access token using a valid refresh token.",
        responses={200: RefreshSerializer, 400: OpenApiResponse(description="Invalid or expired refresh token")}
    )
    def post(self, request, *args, **kwargs):
        logger.info("Token refresh request received.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)
    
class LogoutView(generics.GenericAPIView):
    serializer_class = LogoutSerializer

    @extend_schema(
        summary="User Logout",
        description="Blacklist refresh token and record logout time.",
        responses={200: OpenApiResponse(description="Successfully logged out"), 400: OpenApiResponse(description="Bad Request")}
    )
    def post(self, request):
        logger.info(f"Logout attempt for user: {request.user.email}")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = RefreshToken(serializer.validated_data["refresh"])
        token.blacklist()
        
        AuthenticationService.record_logout(request.user)
        
        return Response({"message": "Successfully logged out"}, status=status.HTTP_200_OK)

class ForgotPasswordView(generics.GenericAPIView):
    serializer_class = ForgotPasswordSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Forgot Password",
        description="Send a 6-digit OTP to user's email for password reset.",
        responses={
            200: OpenApiResponse(description="OTP has been sent"), 
            400: OpenApiResponse(description="No active account found"), 
            500: OpenApiResponse(description="Failed to send OTP")
        }
    )
    def post(self, request):
        logger.info("Forgot password request received.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        user = User.objects.get(email=email, is_active=True, is_deleted=False)
        
        success = AuthenticationService.generate_and_send_otp(user)
        
        if not success:
            return Response(
                {"detail": "Failed to send OTP email. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        return Response(
            {"detail": "OTP has been sent to your email address"},
            status=status.HTTP_200_OK
        )


class VerifyOTPView(generics.GenericAPIView):
    serializer_class = VerifyOTPSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Verify OTP",
        description="Verify if the provided OTP is valid.",
        responses={
            200: OpenApiResponse(description="OTP verified successfully"), 
            400: OpenApiResponse(description="Invalid email or OTP")
        }
    )
    def post(self, request):
        logger.info("OTP verification request received.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        
        try:
            user = User.objects.get(email=email, is_active=True, is_deleted=False)
        except User.DoesNotExist:
            return Response({"detail": "Invalid email address"}, status=status.HTTP_400_BAD_REQUEST)
        
        is_valid, message_or_instance = AuthenticationService.verify_otp(user, otp)
        
        if not is_valid:
            return Response({"detail": message_or_instance}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({"detail": "OTP verified successfully"}, status=status.HTTP_200_OK)


class ResetPasswordView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Reset Password",
        description="Reset the password using a valid OTP and new password.",
        responses={
            200: OpenApiResponse(description="Password has been reset successfully"), 
            400: OpenApiResponse(description="Invalid OTP, email, or passwords do not match")
        }
    )
    def post(self, request):
        logger.info("Password reset request received.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']
        
        try:
            user = User.objects.get(email=email, is_active=True, is_deleted=False)
        except User.DoesNotExist:
            return Response({"detail": "Invalid email address"}, status=status.HTTP_400_BAD_REQUEST)
        
        is_valid, message_or_instance = AuthenticationService.verify_otp(user, otp)
        if not is_valid:
            return Response({"detail": message_or_instance}, status=status.HTTP_400_BAD_REQUEST)
            
        success = AuthenticationService.reset_password(user, message_or_instance, new_password)
        
        if success:
            return Response({"detail": "Password has been reset successfully"}, status=status.HTTP_200_OK)
        return Response({"detail": "Failed to reset password."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

