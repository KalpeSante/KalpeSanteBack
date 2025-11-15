"""
KALPÉ SANTÉ - User Signals
Django signals for user-related events.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import User, Profile, KYCDocument


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create user profile automatically when a new user is created.
    """
    if created and not hasattr(instance, 'profile'):
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def send_welcome_email_on_verification(sender, instance, created, **kwargs):
    """
    Send welcome email when user verifies their email for the first time.
    """
    if not created and instance.email_verified:
        # Check if this is the first time email is verified
        if instance.email_verified_at and \
           (timezone.now() - instance.email_verified_at).seconds < 10:
            from apps.users.tasks import send_welcome_email
            send_welcome_email.delay(instance.id)


@receiver(post_save, sender=KYCDocument)
def notify_kyc_status_change(sender, instance, created, **kwargs):
    """
    Notify user when KYC document status changes.
    """
    if not created:
        # Check if status changed to approved or rejected
        if instance.status == 'approved' and instance.verified_at:
            from apps.users.tasks import notify_kyc_approved
            notify_kyc_approved.delay(instance.user.id)
        elif instance.status == 'rejected' and instance.verified_at:
            from apps.users.tasks import notify_kyc_rejected
            notify_kyc_rejected.delay(instance.user.id, instance.rejection_reason)


@receiver(pre_save, sender=User)
def track_password_change(sender, instance, **kwargs):
    """
    Track when password is changed.
    """
    if instance.pk:
        try:
            old_instance = User.objects.get(pk=instance.pk)
            if old_instance.password != instance.password:
                instance.password_changed_at = timezone.now()
        except User.DoesNotExist:
            pass




