"""
KALPÉ SANTÉ - Core Permissions
Custom permission classes for API access control.
"""

from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner
        return obj.owner == request.user if hasattr(obj, 'owner') else False


class IsOwner(permissions.BasePermission):
    """
    Permission to only allow owners of an object to access it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Check if object has an owner attribute
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        
        # Check if object has a user attribute
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False


class IsSuperAdminOrReadOnly(permissions.BasePermission):
    """
    Permission to only allow super admins to modify, others can read.
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        return request.user and request.user.is_superuser


class IsEmailVerified(permissions.BasePermission):
    """
    Permission to only allow users with verified email.
    """
    message = "Veuillez vérifier votre adresse email avant de continuer."
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            getattr(request.user, 'email_verified', False)
        )


class IsPhoneVerified(permissions.BasePermission):
    """
    Permission to only allow users with verified phone number.
    """
    message = "Veuillez vérifier votre numéro de téléphone avant de continuer."
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            getattr(request.user, 'phone_verified', False)
        )


class IsKYCVerified(permissions.BasePermission):
    """
    Permission to only allow KYC verified users.
    """
    message = "Veuillez compléter votre vérification d'identité (KYC)."
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            getattr(request.user, 'kyc_verified', False)
        )


class HasRole(permissions.BasePermission):
    """
    Permission to check if user has specific role(s).
    Usage: permission_classes = [HasRole & {'roles': ['sponsor', 'admin']}]
    """
    
    def __init__(self, roles=None):
        self.required_roles = roles or []
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'user_type', None)
        return user_role in self.required_roles


class CanAccessMedicalData(permissions.BasePermission):
    """
    Permission to access medical data (HIPAA compliance).
    Only healthcare providers and the patient themselves.
    """
    message = "Vous n'êtes pas autorisé à accéder à ces données médicales."
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Patient can always access their own data
        if hasattr(obj, 'patient') and obj.patient == request.user:
            return True
        
        # Healthcare providers with proper role
        if hasattr(request.user, 'user_type'):
            allowed_types = ['healthcare_provider', 'doctor', 'nurse', 'admin']
            return request.user.user_type in allowed_types
        
        return False


class RateLimitPermission(permissions.BasePermission):
    """
    Permission that implements rate limiting.
    """
    
    def has_permission(self, request, view):
        from django.core.cache import cache
        from django.conf import settings
        
        if request.user.is_authenticated:
            user_id = str(request.user.id)
            cache_key = f'rate_limit:{user_id}:{request.path}'
        else:
            ip = self._get_client_ip(request)
            cache_key = f'rate_limit:anon:{ip}:{request.path}'
        
        # Get current request count
        request_count = cache.get(cache_key, 0)
        
        # Check limit
        max_requests = 100  # per minute
        if request_count >= max_requests:
            return False
        
        # Increment counter
        cache.set(cache_key, request_count + 1, 60)  # 60 seconds TTL
        
        return True
    
    @staticmethod
    def _get_client_ip(request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip




