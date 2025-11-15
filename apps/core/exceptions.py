"""
KALPÉ SANTÉ - Custom Exceptions
Centralized exception handling for consistent API error responses.
"""

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler as drf_exception_handler
from django.utils.translation import gettext_lazy as _
import logging

logger = logging.getLogger('apps.core')


def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF that provides consistent error responses.
    
    Returns:
        Response with standardized error format:
        {
            "error": {
                "code": "error_code",
                "message": "Human-readable error message",
                "details": {...},  # Optional additional details
                "timestamp": "ISO timestamp"
            }
        }
    """
    # Call DRF's default exception handler first
    response = drf_exception_handler(exc, context)
    
    if response is not None:
        # Customize the response format
        custom_response_data = {
            'error': {
                'code': getattr(exc, 'default_code', 'error'),
                'message': str(exc),
                'status_code': response.status_code,
            }
        }
        
        # Add details if available
        if hasattr(exc, 'detail'):
            if isinstance(exc.detail, dict):
                custom_response_data['error']['details'] = exc.detail
            elif isinstance(exc.detail, list):
                custom_response_data['error']['details'] = {'errors': exc.detail}
        
        response.data = custom_response_data
        
        # Log the exception
        logger.error(
            f"API Exception: {exc.__class__.__name__} - {str(exc)}",
            extra={
                'status_code': response.status_code,
                'path': context.get('request').path if context.get('request') else None,
                'method': context.get('request').method if context.get('request') else None,
            }
        )
    
    return response


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class BaseKalpeSanteException(APIException):
    """
    Base exception for all Kalpé Santé custom exceptions.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Une erreur est survenue.')
    default_code = 'error'


# Business Logic Exceptions
# ============================================================================

class InsufficientBalanceException(BaseKalpeSanteException):
    """Raised when wallet balance is insufficient for a transaction."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Solde insuffisant pour effectuer cette transaction.')
    default_code = 'insufficient_balance'


class TransactionLimitExceededException(BaseKalpeSanteException):
    """Raised when transaction exceeds allowed limits."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Le montant dépasse la limite autorisée.')
    default_code = 'transaction_limit_exceeded'


class DailyLimitExceededException(BaseKalpeSanteException):
    """Raised when daily transaction limit is exceeded."""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = _('Limite quotidienne de transactions atteinte.')
    default_code = 'daily_limit_exceeded'


class InvalidTransactionException(BaseKalpeSanteException):
    """Raised when a transaction is invalid."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Transaction invalide.')
    default_code = 'invalid_transaction'


class FrozenWalletException(BaseKalpeSanteException):
    """Raised when attempting to use a frozen wallet."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _('Ce portefeuille est gelé. Veuillez contacter le support.')
    default_code = 'frozen_wallet'


# Healthcare Exceptions
# ============================================================================

class TicketExpiredException(BaseKalpeSanteException):
    """Raised when a health ticket has expired."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Ce ticket de santé a expiré.')
    default_code = 'ticket_expired'


class TicketAlreadyUsedException(BaseKalpeSanteException):
    """Raised when attempting to reuse a ticket."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Ce ticket a déjà été utilisé.')
    default_code = 'ticket_already_used'


class InvalidQRCodeException(BaseKalpeSanteException):
    """Raised when a QR code is invalid."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('QR code invalide.')
    default_code = 'invalid_qr_code'


class UnauthorizedAccessException(BaseKalpeSanteException):
    """Raised when user tries to access unauthorized medical records."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _('Vous n\'êtes pas autorisé à accéder à ces données médicales.')
    default_code = 'unauthorized_medical_access'


# Pharmacy Exceptions
# ============================================================================

class InsufficientStockException(BaseKalpeSanteException):
    """Raised when medication stock is insufficient."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Stock insuffisant pour ce médicament.')
    default_code = 'insufficient_stock'


class InvalidPrescriptionException(BaseKalpeSanteException):
    """Raised when a prescription is invalid."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Ordonnance invalide ou expirée.')
    default_code = 'invalid_prescription'


class MedicationNotAvailableException(BaseKalpeSanteException):
    """Raised when medication is not available."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = _('Médicament non disponible.')
    default_code = 'medication_not_available'


# Payment Exceptions
# ============================================================================

class PaymentFailedException(BaseKalpeSanteException):
    """Raised when a payment fails."""
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = _('Le paiement a échoué. Veuillez réessayer.')
    default_code = 'payment_failed'


class PaymentGatewayException(BaseKalpeSanteException):
    """Raised when payment gateway encounters an error."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = _('Le service de paiement est temporairement indisponible.')
    default_code = 'payment_gateway_error'


class InvalidPaymentMethodException(BaseKalpeSanteException):
    """Raised when payment method is invalid."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Méthode de paiement invalide.')
    default_code = 'invalid_payment_method'


# User/Authentication Exceptions
# ============================================================================

class EmailNotVerifiedException(BaseKalpeSanteException):
    """Raised when user email is not verified."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _('Veuillez vérifier votre adresse email avant de continuer.')
    default_code = 'email_not_verified'


class PhoneNotVerifiedException(BaseKalpeSanteException):
    """Raised when user phone is not verified."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _('Veuillez vérifier votre numéro de téléphone avant de continuer.')
    default_code = 'phone_not_verified'


class KYCNotCompletedException(BaseKalpeSanteException):
    """Raised when KYC is required but not completed."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _('Veuillez compléter votre vérification d\'identité (KYC).')
    default_code = 'kyc_not_completed'


class MFARequiredException(BaseKalpeSanteException):
    """Raised when MFA is required for an action."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _('Authentification à deux facteurs requise.')
    default_code = 'mfa_required'


class InvalidMFACodeException(BaseKalpeSanteException):
    """Raised when MFA code is invalid."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Code d\'authentification invalide.')
    default_code = 'invalid_mfa_code'


# Integration Exceptions
# ============================================================================

class CMUIntegrationException(BaseKalpeSanteException):
    """Raised when CMU API integration fails."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = _('Impossible de se connecter au système CMU.')
    default_code = 'cmu_integration_error'


class ExternalAPIException(BaseKalpeSanteException):
    """Raised when external API call fails."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = _('Service externe temporairement indisponible.')
    default_code = 'external_api_error'


# Wallet & Transaction Exceptions
# ============================================================================

class InsufficientFundsException(BaseKalpeSanteException):
    """Raised when wallet has insufficient funds for transaction."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Solde insuffisant pour effectuer cette transaction.')
    default_code = 'insufficient_funds'


class TransactionException(BaseKalpeSanteException):
    """Raised when transaction processing fails."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Erreur lors du traitement de la transaction.')
    default_code = 'transaction_error'


class WalletLockedException(BaseKalpeSanteException):
    """Raised when attempting to use a locked wallet."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _('Portefeuille verrouillé pour des raisons de sécurité.')
    default_code = 'wallet_locked'


class TransactionLimitExceededException(BaseKalpeSanteException):
    """Raised when transaction limit is exceeded."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Limite de transaction dépassée.')
    default_code = 'transaction_limit_exceeded'


# Security Exceptions
# ============================================================================

class FraudDetectedException(BaseKalpeSanteException):
    """Raised when fraudulent activity is detected."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _('Activité suspecte détectée. Compte temporairement bloqué.')
    default_code = 'fraud_detected'


class RateLimitExceededException(BaseKalpeSanteException):
    """Raised when rate limit is exceeded."""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = _('Trop de requêtes. Veuillez réessayer plus tard.')
    default_code = 'rate_limit_exceeded'


class InvalidSignatureException(BaseKalpeSanteException):
    """Raised when API signature is invalid."""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = _('Signature API invalide.')
    default_code = 'invalid_signature'




