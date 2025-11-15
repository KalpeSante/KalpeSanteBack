"""
KALPÉ SANTÉ - User Serializers
DRF serializers for authentication, registration, and user management.
"""

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from apps.core.serializers import BaseSerializer, TimestampedSerializer
from apps.core.exceptions import (
    EmailNotVerifiedException,
    PhoneNotVerifiedException,
    InvalidMFACodeException,
)
from .models import User, Profile, VerificationCode, KYCDocument, LoginAttempt


class ProfileSerializer(BaseSerializer):
    """Serializer for user profile."""
    
    full_address = serializers.ReadOnlyField()
    has_geolocation = serializers.ReadOnlyField()
    
    class Meta:
        model = Profile
        fields = [
            'nin', 'cmu_number', 'cmu_status',
            'blood_type', 'weight', 'height',
            'allergies', 'medical_history',
            'emergency_contacts',
            'address_line1', 'address_line2', 'city', 'region',
            'postal_code', 'country',
            'latitude', 'longitude',
            'full_address', 'has_geolocation',
            'notifications_enabled', 'email_notifications',
            'sms_notifications', 'push_notifications',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class UserSerializer(BaseSerializer, TimestampedSerializer):
    """Serializer for user details."""
    
    profile = ProfileSerializer(read_only=True)
    age = serializers.ReadOnlyField()
    is_fully_verified = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'phone',
            'date_of_birth', 'user_type', 'age',
            'email_verified', 'email_verified_at',
            'phone_verified', 'phone_verified_at',
            'kyc_verified', 'kyc_verified_at', 'kyc_level',
            'is_fully_verified',
            'mfa_enabled',
            'avatar', 'bio', 'language', 'timezone',
            'onboarding_completed',
            'is_active', 'is_staff',
            'date_joined', 'last_login',
            'created_at', 'updated_at',
            'profile',
        ]
        read_only_fields = [
            'id', 'email_verified', 'email_verified_at',
            'phone_verified', 'phone_verified_at',
            'kyc_verified', 'kyc_verified_at', 'kyc_level',
            'is_fully_verified', 'mfa_enabled',
            'is_active', 'is_staff',
            'date_joined', 'last_login',
            'created_at', 'updated_at',
        ]
        extra_kwargs = {
            'password': {'write_only': True},
        }


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    terms_accepted = serializers.BooleanField(
        write_only=True,
        required=True
    )
    
    class Meta:
        model = User
        fields = [
            'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone',
            'date_of_birth', 'user_type',
            'language', 'terms_accepted',
        ]
    
    def validate(self, attrs):
        """Validate registration data."""
        # Check passwords match
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': _('Les mots de passe ne correspondent pas.')
            })
        
        # Check terms accepted
        if not attrs.get('terms_accepted'):
            raise serializers.ValidationError({
                'terms_accepted': _('Vous devez accepter les conditions d\'utilisation.')
            })
        
        # Remove password_confirm and terms_accepted as they're not model fields
        attrs.pop('password_confirm')
        attrs.pop('terms_accepted')
        
        return attrs
    
    def create(self, validated_data):
        """Create new user."""
        from django.utils import timezone
        
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.terms_accepted_at = timezone.now()
        user.save()
        
        # Create profile
        Profile.objects.create(user=user)
        
        # Send verification email (async task)
        from apps.users.tasks import send_verification_email
        send_verification_email.delay(user.id)
        
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    mfa_code = serializers.CharField(
        required=False,
        write_only=True,
        max_length=6,
        min_length=6
    )
    
    def validate(self, attrs):
        """Validate login credentials."""
        email = attrs.get('email')
        password = attrs.get('password')
        mfa_code = attrs.get('mfa_code')
        
        request = self.context.get('request')
        ip_address = self.context.get('ip_address', '')
        user_agent = self.context.get('user_agent', '')
        
        # Check if user exists
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            LoginAttempt.record_attempt(
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                failure_reason='invalid_credentials'
            )
            raise serializers.ValidationError({
                'non_field_errors': _('Email ou mot de passe invalide.')
            })
        
        # Check if account is locked
        if user.is_account_locked:
            LoginAttempt.record_attempt(
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                failure_reason='account_locked'
            )
            raise serializers.ValidationError({
                'non_field_errors': _('Compte temporairement verrouillé. Veuillez réessayer plus tard.')
            })
        
        # Check if account is active
        if not user.is_active:
            LoginAttempt.record_attempt(
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                failure_reason='account_inactive'
            )
            raise serializers.ValidationError({
                'non_field_errors': _('Ce compte est inactif.')
            })
        
        # Authenticate user
        user = authenticate(request=request, username=email, password=password)
        
        if not user:
            # Record failed attempt
            try:
                failed_user = User.objects.get(email=email)
                failed_user.record_failed_login()
            except User.DoesNotExist:
                pass
            
            LoginAttempt.record_attempt(
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                failure_reason='invalid_credentials'
            )
            raise serializers.ValidationError({
                'non_field_errors': _('Email ou mot de passe invalide.')
            })
        
        # Check MFA if enabled
        if user.mfa_enabled:
            if not mfa_code:
                raise serializers.ValidationError({
                    'mfa_code': _('Code MFA requis.')
                })
            
            if not user.verify_totp(mfa_code):
                LoginAttempt.record_attempt(
                    email=email,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=False,
                    failure_reason='mfa_failed'
                )
                raise InvalidMFACodeException()
        
        # Record successful login
        user.record_successful_login(ip_address=ip_address)
        LoginAttempt.record_attempt(
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True
        )
        
        attrs['user'] = user
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password."""
    
    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        """Validate password change."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': _('Les mots de passe ne correspondent pas.')
            })
        
        return attrs
    
    def validate_old_password(self, value):
        """Validate old password is correct."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(_('Mot de passe actuel incorrect.'))
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for requesting password reset."""
    
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        """Check if email exists."""
        try:
            User.objects.get(email=value)
        except User.DoesNotExist:
            # Don't reveal if email exists or not (security)
            pass
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for confirming password reset."""
    
    code = serializers.CharField(required=True, max_length=6, min_length=6)
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        """Validate password reset."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': _('Les mots de passe ne correspondent pas.')
            })
        return attrs


class VerifyEmailSerializer(serializers.Serializer):
    """Serializer for email verification."""
    
    code = serializers.CharField(required=True, max_length=6, min_length=6)


class VerifyPhoneSerializer(serializers.Serializer):
    """Serializer for phone verification."""
    
    code = serializers.CharField(required=True, max_length=6, min_length=6)


class ResendVerificationSerializer(serializers.Serializer):
    """Serializer for resending verification code."""
    
    verification_type = serializers.ChoiceField(
        required=True,
        choices=['email', 'phone']
    )


class MFAEnableSerializer(serializers.Serializer):
    """Serializer for enabling MFA."""
    
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )


class MFAVerifySerializer(serializers.Serializer):
    """Serializer for verifying MFA setup."""
    
    code = serializers.CharField(required=True, max_length=6, min_length=6)


class MFADisableSerializer(serializers.Serializer):
    """Serializer for disabling MFA."""
    
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    code = serializers.CharField(required=True, max_length=6, min_length=6)


class KYCDocumentSerializer(BaseSerializer, TimestampedSerializer):
    """Serializer for KYC documents."""
    
    verified_by_email = serializers.EmailField(
        source='verified_by.email',
        read_only=True
    )
    is_expired = serializers.ReadOnlyField()
    
    class Meta:
        model = KYCDocument
        fields = [
            'id', 'document_type', 'document_number',
            'document_file', 'status',
            'verified_by', 'verified_by_email', 'verified_at',
            'rejection_reason', 'expires_at', 'is_expired',
            'notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'status', 'verified_by', 'verified_by_email',
            'verified_at', 'rejection_reason', 'is_expired',
            'created_at', 'updated_at',
        ]


class UserListSerializer(BaseSerializer):
    """Serializer for user list (minimal fields)."""
    
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'full_name', 'phone',
            'user_type', 'avatar',
            'email_verified', 'phone_verified', 'kyc_verified',
            'is_active', 'date_joined',
        ]
    
    def get_full_name(self, obj):
        return obj.get_full_name()
