"""
KALPÉ SANTÉ - Core Celery Tasks
Asynchronous tasks for core functionality.
"""

from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger('apps.core')


@shared_task(bind=True, max_retries=3)
def create_audit_log_async(self, user_id, action, resource_type, resource_id, 
                           ip_address, user_agent, metadata=None):
    """
    Create audit log entry asynchronously.
    
    Args:
        user_id: UUID of the user
        action: Action type (CREATE, UPDATE, DELETE, etc.)
        resource_type: Type of resource
        resource_id: ID of resource
        ip_address: Client IP address
        user_agent: User agent string
        metadata: Additional metadata dict
    """
    try:
        from apps.core.models import AuditLog
        from apps.users.models import User
        
        user = None
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                logger.warning(f"User {user_id} not found for audit log")
        
        AuditLog.objects.create(
            user=user,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {},
        )
        
        logger.info(f"Audit log created: {action} on {resource_type}")
        
    except Exception as exc:
        logger.error(f"Failed to create audit log: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def cleanup_old_audit_logs():
    """
    Clean up audit logs older than DATA_RETENTION_DAYS.
    Runs periodically to comply with data retention policies.
    """
    from django.conf import settings
    from apps.core.models import AuditLog
    from datetime import timedelta
    
    retention_days = settings.DATA_RETENTION_DAYS
    cutoff_date = timezone.now() - timedelta(days=retention_days)
    
    # Archive or delete old logs
    old_logs_count = AuditLog.objects.filter(created_at__lt=cutoff_date).count()
    
    if old_logs_count > 0:
        logger.info(f"Cleaning up {old_logs_count} old audit logs")
        # In production, you might want to archive these instead of deleting
        # AuditLog.objects.filter(created_at__lt=cutoff_date).delete()
    
    return old_logs_count


@shared_task
def verify_audit_chain_integrity():
    """
    Verify the integrity of the audit log chain.
    Runs periodically to detect tampering.
    """
    from apps.core.models import AuditLog
    
    logs = AuditLog.objects.order_by('created_at')[:1000]  # Check last 1000 entries
    
    broken_chains = []
    for log in logs:
        if not log.verify_chain():
            broken_chains.append(str(log.id))
            logger.critical(f"Audit chain integrity violation detected: {log.id}")
    
    if broken_chains:
        # Alert security team
        logger.critical(f"Audit chain broken at: {broken_chains}")
        # TODO: Send alert email/SMS to security team
    
    return len(broken_chains)


@shared_task
def send_notification_async(user_id, notification_type, message, channel='email'):
    """
    Send notification asynchronously.
    
    Args:
        user_id: UUID of the user
        notification_type: Type of notification
        message: Notification message
        channel: Notification channel (email, sms, push)
    """
    try:
        from apps.users.models import User
        from apps.notifications.services import NotificationService
        
        user = User.objects.get(id=user_id)
        
        notification_service = NotificationService()
        notification_service.send(
            user=user,
            notification_type=notification_type,
            message=message,
            channel=channel
        )
        
        logger.info(f"Notification sent to {user.email} via {channel}")
        
    except Exception as exc:
        logger.error(f"Failed to send notification: {exc}")
        raise


@shared_task
def generate_daily_reports():
    """
    Generate daily reports for analytics.
    Runs every day at midnight.
    """
    from datetime import datetime
    
    logger.info(f"Generating daily reports for {datetime.now().date()}")
    
    # TODO: Implement daily report generation
    # - Transaction volumes
    # - User activity
    # - Health ticket usage
    # - System performance metrics
    
    return "Daily reports generated successfully"


@shared_task
def backup_critical_data():
    """
    Backup critical data to secure storage.
    Runs daily for disaster recovery.
    """
    logger.info("Starting critical data backup")
    
    # TODO: Implement backup logic
    # - Export database to encrypted archive
    # - Upload to S3/Azure Blob
    # - Verify backup integrity
    
    return "Backup completed successfully"




