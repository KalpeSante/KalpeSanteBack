"""
KALPÉ SANTÉ - User Views
API endpoints for authentication and user management.
"""

from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.utils import timezone
from django.conf import settings
from django.utils.crypto import get_random_string
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from apps.core.permissions import IsOwner, IsEmailVerified, IsPhoneVerified, IsKYCVerified
from apps.core.utils import get_client_ip, get_user_agent, generate_qr_code
from apps.core.exceptions import (
    EmailNotVerifiedException,
    PhoneNotVerifiedException,
    InvalidMFACodeException,
)
from .models import User, Profile, VerificationCode, KYCDocument, UserSession
from .serializers import (
    UserSerializer,
    RegisterSerializer,
    LoginSerializer,
    ChangePasswordSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    VerifyEmailSerializer,
    VerifyPhoneSerializer,
    ResendVerificationSerializer,
    MFAEnableSerializer,
    MFAVerifySerializer,
    MFADisableSerializer,
    KYCDocumentSerializer,
    ProfileSerializer,
    UserListSerializer,
)


@extend_schema(tags=['Authentication'])
class RegisterView(APIView):
    """
    User registration endpoint.
    
    Creates a new user account and sends email verification.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer
    
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Inscription réussie. Veuillez vérifier votre email.',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Authentication'])
class LoginView(APIView):
    """
    User login endpoint with MFA support.
    
    Returns JWT tokens on successful authentication.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer
    
    def post(self, request):
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)
        
        serializer = LoginSerializer(
            data=request.data,
            context={
                'request': request,
                'ip_address': ip_address,
                'user_agent': user_agent,
            }
        )
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        
        # Create session with a unique session key
        # If session exists, Django will create a new one automatically
        if not request.session.session_key:
            request.session.create()
        
        session_key = request.session.session_key
        
        # Check if session already exists and update it, or create new one
        try:
            session = UserSession.objects.get(session_key=session_key)
            session.user = user
            session.ip_address = ip_address
            session.user_agent = user_agent
            session.is_active = True
            session.logged_out_at = None
            session.save()
        except UserSession.DoesNotExist:
            UserSession.objects.create(
                user=user,
                session_key=session_key,
                ip_address=ip_address,
                user_agent=user_agent
            )
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Connexion réussie.',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })


@extend_schema(tags=['Authentication'])
class LogoutView(APIView):
    """
    User logout endpoint.
    
    Blacklists the refresh token and marks session as inactive.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            # Mark session as logged out
            session_key = request.session.session_key
            if session_key:
                UserSession.objects.filter(
                    user=request.user,
                    session_key=session_key,
                    is_active=True
                ).update(
                    is_active=False,
                    logged_out_at=timezone.now()
                )
            
            return Response({
                'message': _('Déconnexion réussie.')
            })
        except Exception as e:
            return Response({
                'message': _('Erreur lors de la déconnexion.')
            }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Authentication'])
class VerifyEmailView(APIView):
    """
    Email verification endpoint.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = VerifyEmailSerializer
    
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        code = serializer.validated_data['code']
        
        # Find valid verification code
        try:
            verification = VerificationCode.objects.get(
                user=request.user,
                code_type='email',
                code=code,
                is_used=False
            )
            
            if not verification.is_valid:
                return Response({
                    'error': _('Code expiré.')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Mark code as used and verify email
            verification.use_code()
            request.user.verify_email()
            
            return Response({
                'message': _('Email vérifié avec succès.')
            })
            
        except VerificationCode.DoesNotExist:
            return Response({
                'error': _('Code invalide.')
            }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Authentication'])
class VerifyPhoneView(APIView):
    """
    Phone verification endpoint.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = VerifyPhoneSerializer
    
    def post(self, request):
        serializer = VerifyPhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        code = serializer.validated_data['code']
        
        # Find valid verification code
        try:
            verification = VerificationCode.objects.get(
                user=request.user,
                code_type='phone',
                code=code,
                is_used=False
            )
            
            if not verification.is_valid:
                return Response({
                    'error': _('Code expiré.')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Mark code as used and verify phone
            verification.use_code()
            request.user.verify_phone()
            
            return Response({
                'message': _('Téléphone vérifié avec succès.')
            })
            
        except VerificationCode.DoesNotExist:
            return Response({
                'error': _('Code invalide.')
            }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Authentication'])
class ResendVerificationView(APIView):
    """
    Resend verification code (email or phone).
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ResendVerificationSerializer
    
    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        verification_type = serializer.validated_data['verification_type']
        
        # Generate new code
        code = VerificationCode.generate_code(
            user=request.user,
            code_type=verification_type
        )
        
        # Send code (async)
        if verification_type == 'email':
            from apps.users.tasks import send_verification_email
            send_verification_email.delay(request.user.id, code.code)
        else:
            from apps.users.tasks import send_verification_sms
            send_verification_sms.delay(request.user.id, code.code)
        
        return Response({
            'message': 'Code de vérification envoyé.'
        })


@extend_schema(tags=['Authentication'])
class PasswordResetRequestView(APIView):
    """
    Request password reset code.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetRequestSerializer
    
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email)
            
            # Generate reset code
            code = VerificationCode.generate_code(
                user=user,
                code_type='password_reset',
                expiry_minutes=30
            )
            
            # Send code (async)
            from apps.users.tasks import send_password_reset_email
            send_password_reset_email.delay(user.id, code.code)
            
        except User.DoesNotExist:
            # Don't reveal if email exists
            pass
        
        return Response({
            'message': 'Si votre email existe, vous recevrez un code de réinitialisation.'
        })


@extend_schema(tags=['Authentication'])
class PasswordResetConfirmView(APIView):
    """
    Confirm password reset with code.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetConfirmSerializer
    
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        code = serializer.validated_data['code']
        new_password = serializer.validated_data['new_password']
        
        try:
            verification = VerificationCode.objects.get(
                code_type='password_reset',
                code=code,
                is_used=False
            )
            
            if not verification.is_valid:
                return Response({
                    'error': 'Code expiré.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Reset password
            user = verification.user
            user.set_password(new_password)
            user.password_changed_at = timezone.now()
            user.save()
            
            # Mark code as used
            verification.use_code()
            
            return Response({
                'message': 'Mot de passe réinitialisé avec succès.'
            })
            
        except VerificationCode.DoesNotExist:
            return Response({
                'error': _('Code invalide.')
            }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    list=extend_schema(tags=['Users']),
    retrieve=extend_schema(tags=['Users']),
    update=extend_schema(tags=['Users']),
    partial_update=extend_schema(tags=['Users']),
)
class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user management.
    
    list: List all users (admin only)
    retrieve: Get user details
    update: Update user
    partial_update: Partially update user
    me: Get current user profile
    change_password: Change password
    enable_mfa: Enable MFA
    disable_mfa: Disable MFA
    """
    queryset = User.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        return UserSerializer
    
    def get_permissions(self):
        if self.action in ['list']:
            return [permissions.IsAdminUser()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsOwner()]
        return [permissions.IsAuthenticated()]
    
    @extend_schema(tags=['Users'])
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user profile."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    @extend_schema(tags=['Users'])
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change user password."""
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.password_changed_at = timezone.now()
        request.user.save()
        
        return Response({
            'message': 'Mot de passe modifié avec succès.'
        })
    
    @extend_schema(tags=['Users', 'MFA'])
    @action(detail=False, methods=['post'])
    def enable_mfa(self, request):
        """Enable MFA and return QR code."""
        serializer = MFAEnableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Verify password
        if not request.user.check_password(serializer.validated_data['password']):
            return Response({
                'error': 'Mot de passe incorrect.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Enable MFA
        secret = request.user.enable_mfa()
        totp_uri = request.user.get_totp_uri()
        
        # Generate QR code
        qr_code = generate_qr_code(totp_uri)
        
        return Response({
            'message': 'MFA activé. Scannez le QR code avec votre application d\'authentification.',
            'secret': secret,
            'qr_code_uri': totp_uri,
            'backup_codes': request.user.backup_codes,
        })
    
    @extend_schema(tags=['Users', 'MFA'])
    @action(detail=False, methods=['post'])
    def disable_mfa(self, request):
        """Disable MFA."""
        serializer = MFADisableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Verify password
        if not request.user.check_password(serializer.validated_data['password']):
            return Response({
                'error': 'Mot de passe incorrect.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify MFA code
        if not request.user.verify_totp(serializer.validated_data['code']):
            raise InvalidMFACodeException()
        
        # Disable MFA
        request.user.disable_mfa()
        
        return Response({
            'message': 'MFA désactivé avec succès.'
        })


@extend_schema_view(
    list=extend_schema(tags=['KYC']),
    retrieve=extend_schema(tags=['KYC']),
    create=extend_schema(tags=['KYC']),
)
class KYCDocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for KYC document management.
    
    list: List user's KYC documents
    retrieve: Get KYC document details
    create: Upload new KYC document
    approve: Approve KYC document (admin only)
    reject: Reject KYC document (admin only)
    """
    serializer_class = KYCDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return KYCDocument.objects.all()
        return KYCDocument.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @extend_schema(tags=['KYC'])
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        """Approve KYC document."""
        document = self.get_object()
        document.approve(verified_by=request.user)
        
        # Check if user should be KYC verified
        approved_docs = KYCDocument.objects.filter(
            user=document.user,
            status='approved'
        ).count()
        
        if approved_docs >= 2:  # Require at least 2 documents
            document.user.complete_kyc(level=2)
        
        return Response({
            'message': 'Document approuvé.',
            'document': KYCDocumentSerializer(document).data
        })
    
    @extend_schema(tags=['KYC'])
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def reject(self, request, pk=None):
        """Reject KYC document."""
        document = self.get_object()
        reason = request.data.get('reason', '')
        
        if not reason:
            return Response({
                'error': 'Raison du rejet requise.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        document.reject(verified_by=request.user, reason=reason)
        
        return Response({
            'message': 'Document rejeté.',
            'document': KYCDocumentSerializer(document).data
        })
