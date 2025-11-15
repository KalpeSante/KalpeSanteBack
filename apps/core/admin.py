"""
KALPÉ SANTÉ - Core Admin
Django admin configuration for core models.
"""

from django.contrib import admin
from django.utils.html import format_html
from apps.core.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Admin interface for AuditLog model.
    Read-only to preserve audit trail integrity.
    """
    list_display = [
        'id_short',
        'action',
        'user',
        'resource_type',
        'resource_id_short',
        'ip_address',
        'created_at',
        'chain_status',
    ]
    list_filter = [
        'action',
        'resource_type',
        'created_at',
    ]
    search_fields = [
        'user__email',
        'user__phone',
        'resource_id',
        'ip_address',
    ]
    readonly_fields = [
        'id',
        'user',
        'action',
        'resource_type',
        'resource_id',
        'ip_address',
        'user_agent',
        'changes',
        'metadata',
        'previous_hash',
        'current_hash',
        'created_at',
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    # Make all fields read-only
    def has_add_permission(self, request):
        """Disable manual addition of audit logs."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Disable deletion of audit logs."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable modification of audit logs."""
        return False
    
    @admin.display(description='ID')
    def id_short(self, obj):
        """Display short version of UUID."""
        return str(obj.id)[:8] + '...'
    
    @admin.display(description='Resource ID')
    def resource_id_short(self, obj):
        """Display short version of resource UUID."""
        return str(obj.resource_id)[:8] + '...'
    
    @admin.display(description='Chain Integrity')
    def chain_status(self, obj):
        """Display chain verification status."""
        is_valid = obj.verify_chain()
        if is_valid:
            return format_html(
                '<span style="color: green;">✓ Valid</span>'
            )
        else:
            return format_html(
                '<span style="color: red;">✗ Broken</span>'
            )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('user')
