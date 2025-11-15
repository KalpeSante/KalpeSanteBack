"""
KALPÉ SANTÉ - User Admin
Django admin configuration for user models.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import User, Profile, VerificationCode, KYCDocument, UserSession, LoginAttempt


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin for User model."""
    
    list_display = [
        'email', 'full_name_display', 'user_type',
        'verification_status', 'mfa_status',
        'is_active', 'date_joined',
    ]
    list_filter = [
        'user_type', 'email_verified', 'phone_verified',
        'kyc_verified', 'mfa_enabled', 'is_active', 'is_staff',
    ]
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {
            'fields': ('email', 'password')
        }),
        (_('Personal Info'), {
            'fields': ('first_name', 'last_name', 'phone', 'date_of_birth', 'avatar', 'bio')
        }),
        (_('Role'), {
            'fields': ('user_type',)
        }),
        (_('Verification'), {
            'fields': (
                'email_verified', 'email_verified_at',
                'phone_verified', 'phone_verified_at',
                'kyc_verified', 'kyc_verified_at', 'kyc_level',
            )
        }),
        (_('Security'), {
            'fields': (
                'mfa_enabled', 'failed_login_attempts',
                'locked_until', 'last_login_ip', 'password_changed_at',
            )
        }),
        (_('Preferences'), {
            'fields': ('language', 'timezone', 'onboarding_completed')
        }),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        (_('Important dates'), {
            'fields': ('last_login', 'date_joined', 'terms_accepted_at')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'first_name', 'last_name', 'phone',
                'user_type', 'password1', 'password2'
            ),
        }),
    )
    
    readonly_fields = [
        'email_verified_at', 'phone_verified_at', 'kyc_verified_at',
        'last_login_ip', 'password_changed_at', 'last_login',
        'date_joined', 'terms_accepted_at',
    ]
    
    @admin.display(description='Full Name')
    def full_name_display(self, obj):
        return obj.get_full_name()
    
    @admin.display(description='Verification')
    def verification_status(self, obj):
        statuses = []
        if obj.email_verified:
            statuses.append('<span style="color: green;">✓ Email</span>')
        else:
            statuses.append('<span style="color: red;">✗ Email</span>')
        
        if obj.phone_verified:
            statuses.append('<span style="color: green;">✓ Phone</span>')
        else:
            statuses.append('<span style="color: red;">✗ Phone</span>')
        
        if obj.kyc_verified:
            statuses.append(f'<span style="color: green;">✓ KYC (L{obj.kyc_level})</span>')
        else:
            statuses.append('<span style="color: red;">✗ KYC</span>')
        
        return format_html('<br>'.join(statuses))
    
    @admin.display(description='MFA')
    def mfa_status(self, obj):
        if obj.mfa_enabled:
            return format_html('<span style="color: green;">✓ Enabled</span>')
        return format_html('<span style="color: gray;">Disabled</span>')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile')


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Admin for user profiles."""
    
    list_display = ['user', 'nin', 'cmu_number', 'cmu_status', 'blood_type']
    list_filter = ['cmu_status', 'blood_type']
    search_fields = ['user__email', 'nin', 'cmu_number']
    readonly_fields = ['user', 'created_at', 'updated_at']


@admin.register(VerificationCode)
class VerificationCodeAdmin(admin.ModelAdmin):
    """Admin for verification codes."""
    
    list_display = ['user', 'code_type', 'code', 'is_used', 'expires_at', 'created_at']
    list_filter = ['code_type', 'is_used', 'created_at']
    search_fields = ['user__email', 'code']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


@admin.register(KYCDocument)
class KYCDocumentAdmin(admin.ModelAdmin):
    """Admin for KYC documents."""
    
    list_display = [
        'user', 'document_type', 'status',
        'verified_by', 'verified_at', 'created_at'
    ]
    list_filter = ['status', 'document_type', 'created_at']
    search_fields = ['user__email', 'document_number']
    readonly_fields = ['user', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('user', 'document_type', 'document_number', 'document_file')
        }),
        (_('Status'), {
            'fields': ('status', 'verified_by', 'verified_at', 'rejection_reason')
        }),
        (_('Additional Info'), {
            'fields': ('expires_at', 'notes')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """Admin for user sessions."""
    
    list_display = [
        'user', 'ip_address', 'device_type',
        'is_active', 'created_at', 'last_activity'
    ]
    list_filter = ['is_active', 'device_type', 'created_at']
    search_fields = ['user__email', 'ip_address', 'session_key']
    readonly_fields = ['created_at', 'last_activity']
    date_hierarchy = 'created_at'


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    """Admin for login attempts."""
    
    list_display = [
        'email', 'ip_address', 'success',
        'failure_reason', 'created_at'
    ]
    list_filter = ['success', 'failure_reason', 'created_at']
    search_fields = ['email', 'ip_address']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
