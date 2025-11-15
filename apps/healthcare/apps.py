"""
KALPÉ SANTÉ - Healthcare App Configuration
"""

from django.apps import AppConfig


class HealthcareConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.healthcare'
    verbose_name = 'Healthcare & Medical Services'
    
    def ready(self):
        """Import signals when app is ready."""
        import apps.healthcare.signals  # noqa
