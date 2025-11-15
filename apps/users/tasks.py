"""
KALPÉ SANTÉ - User Tasks
Celery tasks for email/SMS verification and notifications.
"""

from celery import shared_task
from django.utils import timezone
from django.conf import settings
import logging

logger = logging.getLogger('apps.users')


@shared_task(bind=True, max_retries=3)
def send_verification_email(self, user_id, code=None):
    """
    Send email verification code.
    
    Args:
        user_id: UUID of the user
        code: Verification code (generated if not provided)
    """
    try:
        from apps.users.models import User, VerificationCode
        
        user = User.objects.get(id=user_id)
        
        if not code:
            verification = VerificationCode.generate_code(
                user=user,
                code_type='email'
            )
            code = verification.code
        
        # TODO: Use proper email template
        subject = 'KALPÉ SANTÉ - Vérification Email'
        message = f"""
        Bonjour {user.first_name},
        
        Votre code de vérification est: {code}
        
        Ce code expire dans 15 minutes.
        
        Si vous n'avez pas demandé ce code, ignorez cet email.
        
        Cordialement,
        L'équipe KALPÉ SANTÉ
        """
        
        # Send email (using Django's send_mail for now)
        from django.core.mail import send_mail
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        logger.info(f"Verification email sent to {user.email}")
        
    except Exception as exc:
        logger.error(f"Failed to send verification email: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_verification_sms(self, user_id, code=None):
    """
    Send phone verification code via SMS.
    
    Args:
        user_id: UUID of the user
        code: Verification code (generated if not provided)
    """
    try:
        from apps.users.models import User, VerificationCode
        
        user = User.objects.get(id=user_id)
        
        if not code:
            verification = VerificationCode.generate_code(
                user=user,
                code_type='phone'
            )
            code = verification.code
        
        message = f"KALPÉ SANTÉ: Votre code de vérification est {code}. Valide 15 min."
        
        # TODO: Integrate with Twilio or Africa's Talking
        # For now, just log
        logger.info(f"SMS would be sent to {user.phone}: {message}")
        
        # Uncomment when SMS service is configured:
        # from twilio.rest import Client
        # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        # client.messages.create(
        #     body=message,
        #     from_=settings.TWILIO_PHONE_NUMBER,
        #     to=user.phone
        # )
        
        logger.info(f"Verification SMS sent to {user.phone}")
        
    except Exception as exc:
        logger.error(f"Failed to send verification SMS: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_password_reset_email(self, user_id, code):
    """
    Send password reset code via email.
    
    Args:
        user_id: UUID of the user
        code: Reset code
    """
    try:
        from apps.users.models import User
        
        user = User.objects.get(id=user_id)
        
        subject = 'KALPÉ SANTÉ - Réinitialisation Mot de Passe'
        message = f"""
        Bonjour {user.first_name},
        
        Vous avez demandé la réinitialisation de votre mot de passe.
        
        Votre code de réinitialisation est: {code}
        
        Ce code expire dans 30 minutes.
        
        Si vous n'avez pas demandé cette réinitialisation, ignorez cet email et
        contactez-nous immédiatement si vous pensez que votre compte est compromis.
        
        Cordialement,
        L'équipe KALPÉ SANTÉ
        """
        
        from django.core.mail import send_mail
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        logger.info(f"Password reset email sent to {user.email}")
        
    except Exception as exc:
        logger.error(f"Failed to send password reset email: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def cleanup_expired_verification_codes():
    """
    Clean up expired verification codes.
    Runs daily.
    """
    from apps.users.models import VerificationCode
    
    expired_codes = VerificationCode.objects.filter(
        expires_at__lt=timezone.now(),
        is_used=False
    )
    
    count = expired_codes.count()
    expired_codes.delete()
    
    logger.info(f"Cleaned up {count} expired verification codes")
    return count


@shared_task
def cleanup_inactive_sessions():
    """
    Clean up inactive user sessions older than 30 days.
    Runs daily.
    """
    from apps.users.models import UserSession
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=30)
    
    old_sessions = UserSession.objects.filter(
        last_activity__lt=cutoff_date,
        is_active=False
    )
    
    count = old_sessions.count()
    old_sessions.delete()
    
    logger.info(f"Cleaned up {count} old user sessions")
    return count


@shared_task
def send_welcome_email(user_id):
    """
    Send welcome email to new users after email verification.
    
    Args:
        user_id: UUID of the user
    """
    try:
        from apps.users.models import User
        
        user = User.objects.get(id=user_id)
        
        subject = 'Bienvenue sur KALPÉ SANTÉ!'
        message = f"""
        Bonjour {user.first_name},
        
        Bienvenue sur KALPÉ SANTÉ! Votre compte est maintenant actif.
        
        Vous pouvez maintenant:
        - Gérer votre portefeuille électronique
        - Créer des tickets de santé
        - Consulter vos dossiers médicaux
        - Et bien plus encore!
        
        Si vous avez des questions, n'hésitez pas à nous contacter.
        
        Cordialement,
        L'équipe KALPÉ SANTÉ
        """
        
        from django.core.mail import send_mail
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,  # Don't fail if welcome email fails
        )
        
        logger.info(f"Welcome email sent to {user.email}")
        
    except Exception as exc:
        logger.error(f"Failed to send welcome email: {exc}")


@shared_task
def notify_kyc_approved(user_id):
    """
    Notify user when KYC is approved.
    
    Args:
        user_id: UUID of the user
    """
    try:
        from apps.users.models import User
        
        user = User.objects.get(id=user_id)
        
        subject = 'KALPÉ SANTÉ - Vérification KYC Approuvée'
        message = f"""
        Bonjour {user.first_name},
        
        Bonne nouvelle! Votre vérification d'identité (KYC) a été approuvée.
        
        Votre compte est maintenant entièrement vérifié et vous avez accès
        à toutes les fonctionnalités de la plateforme.
        
        Merci de votre confiance!
        
        Cordialement,
        L'équipe KALPÉ SANTÉ
        """
        
        from django.core.mail import send_mail
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
        
        logger.info(f"KYC approval notification sent to {user.email}")
        
    except Exception as exc:
        logger.error(f"Failed to send KYC approval notification: {exc}")


@shared_task
def notify_kyc_rejected(user_id, reason):
    """
    Notify user when KYC is rejected.
    
    Args:
        user_id: UUID of the user
        reason: Rejection reason
    """
    try:
        from apps.users.models import User
        
        user = User.objects.get(id=user_id)
        
        subject = 'KALPÉ SANTÉ - Vérification KYC Non Approuvée'
        message = f"""
        Bonjour {user.first_name},
        
        Malheureusement, votre vérification d'identité (KYC) n'a pas été approuvée
        pour la raison suivante:
        
        {reason}
        
        Veuillez soumettre de nouveaux documents conformes aux exigences.
        
        Si vous avez des questions, contactez notre support.
        
        Cordialement,
        L'équipe KALPÉ SANTÉ
        """
        
        from django.core.mail import send_mail
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
        
        logger.info(f"KYC rejection notification sent to {user.email}")
        
    except Exception as exc:
        logger.error(f"Failed to send KYC rejection notification: {exc}")
