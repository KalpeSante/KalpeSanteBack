"""
KALPÉ SANTÉ - Wallet Signals
Signal handlers for wallet events.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Wallet, Transaction
from apps.core.models import AuditLog


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_wallet_for_new_user(sender, instance, created, **kwargs):
    """Automatically create a wallet when a new user is registered."""
    if created:
        Wallet.objects.create(
            user=instance,
            currency='XOF'
        )


@receiver(post_save, sender=Transaction)
def log_transaction_event(sender, instance, created, **kwargs):
    """Log transaction events to audit log."""
    if created:
        action = AuditLog.CREATE
        action_description = f"Transaction created: {instance.transaction_type}"
    else:
        action = AuditLog.UPDATE
        action_description = f"Transaction updated: {instance.status}"
    
    AuditLog.objects.create(
        user=instance.initiated_by,
        action=action,
        resource_type='Transaction',
        resource_id=str(instance.id),
        ip_address='127.0.0.1',  # Should be captured from request
        user_agent='System',
        changes={
            'action_description': action_description,
            'transaction_type': instance.transaction_type,
            'status': instance.status,
            'amount': str(instance.amount),
            'reference': instance.reference,
            'fraud_score': instance.fraud_score,
            'is_flagged': instance.is_flagged,
        }
    )


@receiver(post_save, sender=Transaction)
def check_high_value_transaction(sender, instance, created, **kwargs):
    """Flag high-value transactions for additional review."""
    if created and instance.amount >= 1000000:  # 1 million XOF
        if not instance.is_flagged:
            instance.flag_for_review(
                reason=f"High-value transaction: {instance.amount} XOF"
            )


