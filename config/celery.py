"""
KALPÉ SANTÉ - Celery Configuration
Asynchronous task queue configuration.
"""

import os
from celery import Celery
from django.conf import settings

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

# Create Celery app
app = Celery('kalpe_sante')

# Load configuration from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


# Celery Beat Schedule (Periodic Tasks)
app.conf.beat_schedule = {
    # Cleanup old audit logs daily at 2 AM
    'cleanup-old-audit-logs': {
        'task': 'apps.core.tasks.cleanup_old_audit_logs',
        'schedule': 86400.0,  # 24 hours
        'options': {'expires': 3600}
    },
    
    # Verify audit chain integrity every 6 hours
    'verify-audit-chain': {
        'task': 'apps.core.tasks.verify_audit_chain_integrity',
        'schedule': 21600.0,  # 6 hours
        'options': {'expires': 3600}
    },
    
    # Generate daily reports at midnight
    'generate-daily-reports': {
        'task': 'apps.core.tasks.generate_daily_reports',
        'schedule': 86400.0,  # 24 hours
        'options': {'expires': 3600}
    },
    
    # Backup critical data daily at 3 AM
    'backup-critical-data': {
        'task': 'apps.core.tasks.backup_critical_data',
        'schedule': 86400.0,  # 24 hours
        'options': {'expires': 3600}
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery configuration."""
    print(f'Request: {self.request!r}')




