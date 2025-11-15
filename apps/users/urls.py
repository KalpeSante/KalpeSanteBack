"""
KALPÉ SANTÉ - User URLs
API endpoints routing for authentication and user management.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    VerifyEmailView,
    VerifyPhoneView,
    ResendVerificationView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    UserViewSet,
    KYCDocumentViewSet,
)

# Create router for viewsets
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'kyc', KYCDocumentViewSet, basename='kyc')

urlpatterns = [
    # Authentication
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Verification
    path('auth/verify-email/', VerifyEmailView.as_view(), name='verify_email'),
    path('auth/verify-phone/', VerifyPhoneView.as_view(), name='verify_phone'),
    path('auth/resend-verification/', ResendVerificationView.as_view(), name='resend_verification'),
    
    # Password Reset
    path('auth/password-reset/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('auth/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    
    # Router URLs
    path('', include(router.urls)),
]
