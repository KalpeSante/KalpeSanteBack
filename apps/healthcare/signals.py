"""
KALPÉ SANTÉ - Healthcare Signals
Signal handlers for healthcare events.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import HealthTicket, Prescription
from apps.core.models import AuditLog


@receiver(post_save, sender=HealthTicket)
def log_health_ticket_event(sender, instance, created, **kwargs):
    """Log health ticket events to audit log."""
    if created:
        action = AuditLog.CREATE
        action_description = f"Health ticket created: {instance.ticket_number}"
    else:
        action = AuditLog.UPDATE
        action_description = f"Health ticket updated: {instance.status}"
    
    AuditLog.objects.create(
        user=instance.patient,
        action=action,
        resource_type='HealthTicket',
        resource_id=str(instance.id),
        ip_address='127.0.0.1',
        user_agent='System',
        changes={
            'action_description': action_description,
            'ticket_number': instance.ticket_number,
            'status': instance.status,
            'provider': instance.provider.name,
            'patient': instance.patient.get_full_name(),
        }
    )


@receiver(post_save, sender=Prescription)
def log_prescription_event(sender, instance, created, **kwargs):
    """Log prescription events to audit log."""
    if created:
        action = AuditLog.CREATE
        action_description = f"Prescription created: {instance.prescription_number}"
    else:
        action = AuditLog.UPDATE
        action_description = f"Prescription updated"
    
    AuditLog.objects.create(
        user=instance.doctor,
        action=action,
        resource_type='Prescription',
        resource_id=str(instance.id),
        ip_address='127.0.0.1',
        user_agent='System',
        changes={
            'action_description': action_description,
            'prescription_number': instance.prescription_number,
            'patient': instance.patient.get_full_name(),
            'doctor': instance.doctor.get_full_name(),
            'is_dispensed': instance.is_dispensed,
        }
    )

