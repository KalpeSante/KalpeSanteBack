"""
KALPÉ SANTÉ - Custom Middleware
Security and audit middleware for request/response processing.
"""

import logging
import json
import time
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from apps.core.models import AuditLog

logger = logging.getLogger('apps.core')
audit_logger = logging.getLogger('audit')


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all HTTP requests for monitoring and debugging.
    Logs request method, path, user, IP, response status, and duration.
    """
    
    def process_request(self, request):
        """Store request start time."""
        request.start_time = time.time()
        return None
    
    def process_response(self, request, response):
        """
Log request details after response is generated.
        """
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            
            log_data = {
                'method': request.method,
                'path': request.path,
                'status': response.status_code,
                'duration_ms': round(duration * 1000, 2),
                'user': str(request.user) if request.user.is_authenticated else 'Anonymous',
                'ip': self._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
            }
            
            # Log based on response status
            if response.status_code >= 500:
                logger.error(f"Server Error: {json.dumps(log_data)}")
            elif response.status_code >= 400:
                logger.warning(f"Client Error: {json.dumps(log_data)}")
            else:
                logger.info(f"Request: {json.dumps(log_data)}")
        
        return response
    
    @staticmethod
    def _get_client_ip(request):
        """Extract client IP address from request headers."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AuditMiddleware(MiddlewareMixin):
    """
    Middleware for comprehensive audit logging of sensitive operations.
    Automatically logs modifications to critical resources (HIPAA/RGPD compliance).
    """
    
    # Paths that should be audited
    AUDIT_PATHS = [
        '/api/v1/wallet/',
        '/api/v1/healthcare/',
        '/api/v1/pharmacy/',
        '/api/v1/users/',
        '/api/v1/payments/',
    ]
    
    # Methods that modify data
    AUDIT_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']
    
    def process_request(self, request):
        """
        Store request data for audit logging.
        """
        if not settings.ENABLE_AUDIT_LOGGING:
            return None
        
        # Check if this request should be audited
        if self._should_audit(request):
            request.audit_data = {
                'method': request.method,
                'path': request.path,
                'user': request.user if request.user.is_authenticated else None,
                'ip': RequestLoggingMiddleware._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
            }
        
        return None
    
    def process_response(self, request, response):
        """
        Log audit trail after successful operations.
        """
        if not settings.ENABLE_AUDIT_LOGGING:
            return response
        
        # Only log successful modifications
        if (hasattr(request, 'audit_data') and 
            200 <= response.status_code < 300):
            
            try:
                self._create_audit_log(request, response)
            except Exception as e:
                logger.error(f"Failed to create audit log: {e}")
        
        return response
    
    def _should_audit(self, request):
        """
        Determine if this request should be audited.
        """
        # Only audit authenticated users
        if not request.user.is_authenticated:
            return False
        
        # Only audit modification methods
        if request.method not in self.AUDIT_METHODS:
            return False
        
        # Only audit specific paths
        return any(request.path.startswith(path) for path in self.AUDIT_PATHS)
    
    def _create_audit_log(self, request, response):
        """
        Create an audit log entry.
        """
        audit_data = request.audit_data
        
        # Extract resource information from request/response
        resource_type = self._extract_resource_type(request.path)
        resource_id = self._extract_resource_id(request, response)
        
        # Map HTTP method to audit action
        action_map = {
            'POST': AuditLog.CREATE,
            'PUT': AuditLog.UPDATE,
            'PATCH': AuditLog.UPDATE,
            'DELETE': AuditLog.DELETE,
        }
        
        # Create audit log asynchronously to avoid impacting response time
        try:
            from apps.core.tasks import create_audit_log_async
            create_audit_log_async.delay(
                user_id=str(audit_data['user'].id) if audit_data['user'] else None,
                action=action_map.get(request.method, AuditLog.ACCESS),
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=audit_data['ip'],
                user_agent=audit_data['user_agent'],
                metadata={
                    'path': request.path,
                    'method': request.method,
                    'status_code': response.status_code,
                }
            )
        except ImportError:
            # Fallback to synchronous logging if Celery is not available
            audit_logger.info(f"Audit: {json.dumps(audit_data)}")
    
    @staticmethod
    def _extract_resource_type(path):
        """Extract resource type from URL path."""
        parts = path.strip('/').split('/')
        if len(parts) >= 3:
            return parts[2].capitalize()  # e.g., /api/v1/wallet/ -> Wallet
        return 'Unknown'
    
    @staticmethod
    def _extract_resource_id(request, response):
        """
        Extract resource ID from request or response.
        """
        # Try to get from URL
        path_parts = request.path.strip('/').split('/')
        for part in path_parts:
            # Check if it's a UUID
            if len(part) == 36 and part.count('-') == 4:
                return part
        
        # Try to get from response body
        try:
            if hasattr(response, 'data') and isinstance(response.data, dict):
                return response.data.get('id', '')
        except:
            pass
        
        return ''


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Add security headers to all responses.
    Implements OWASP security best practices.
    """
    
    def process_response(self, request, response):
        """Add security headers."""
        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # XSS Protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Prevent clickjacking
        response['X-Frame-Options'] = 'DENY'
        
        # Referrer Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Content Security Policy
        if not settings.DEBUG:
            response['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            )
        
        # Permissions Policy (formerly Feature Policy)
        response['Permissions-Policy'] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=()"
        )
        
        return response




