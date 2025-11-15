"""
KALPÉ SANTÉ - Custom Validators
Reusable validators for data validation across the application.
"""

import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator


# Phone Number Validators
# ============================================================================

class SenegalPhoneValidator(RegexValidator):
    """
    Validator for Senegalese phone numbers.
    Accepts formats: +221XXXXXXXXX, 221XXXXXXXXX, 7XXXXXXXX, 33XXXXXXX
    """
    regex = r'^(\+?221|0)?[73]\d{8}$'
    message = _(
        'Numéro de téléphone invalide. Format attendu: +221XXXXXXXXX '
        'ou 7XXXXXXXX (mobile) ou 33XXXXXXX (fixe).'
    )
    code = 'invalid_senegal_phone'


def validate_senegal_phone(value):
    """
    Validate Senegalese phone number format.
    """
    # Remove spaces and dashes
    cleaned = re.sub(r'[\s\-()]', '', value)
    
    # Check format
    if not re.match(r'^(\+?221|0)?[73]\d{8}$', cleaned):
        raise ValidationError(
            _('Numéro de téléphone sénégalais invalide.'),
            code='invalid_senegal_phone'
        )
    
    return cleaned


# National Identification Number (NIN) Validator
# ============================================================================

def validate_nin(value):
    """
    Validate Senegalese National Identification Number (NIN).
    Format: 13 digits
    """
    if not value:
        return
    
    # Remove spaces
    cleaned = value.replace(' ', '')
    
    # Check if it's 13 digits
    if not re.match(r'^\d{13}$', cleaned):
        raise ValidationError(
            _('Numéro d\'Identification National invalide. Doit contenir 13 chiffres.'),
            code='invalid_nin'
        )
    
    return cleaned


# Amount Validators
# ============================================================================

def validate_positive_amount(value):
    """
    Validate that amount is positive and has max 2 decimal places.
    """
    if value <= 0:
        raise ValidationError(
            _('Le montant doit être supérieur à zéro.'),
            code='invalid_amount'
        )
    
    # Check decimal places
    if round(value, 2) != value:
        raise ValidationError(
            _('Le montant ne peut avoir plus de 2 décimales.'),
            code='invalid_decimal_places'
        )


def validate_transaction_amount(value):
    """
    Validate transaction amount against min/max limits.
    """
    from django.conf import settings
    
    validate_positive_amount(value)
    
    min_amount = settings.MIN_TRANSACTION_AMOUNT
    max_amount = settings.MAX_TRANSACTION_AMOUNT
    
    if value < min_amount:
        raise ValidationError(
            _('Le montant minimum est de %(min)s XOF.') % {'min': min_amount},
            code='amount_too_low'
        )
    
    if value > max_amount:
        raise ValidationError(
            _('Le montant maximum est de %(max)s XOF.') % {'max': max_amount},
            code='amount_too_high'
        )


# File Validators
# ============================================================================

def validate_image_size(value):
    """
    Validate image file size (max 5MB).
    """
    max_size_mb = 5
    if value.size > max_size_mb * 1024 * 1024:
        raise ValidationError(
            _('La taille de l\'image ne doit pas dépasser %(max)s MB.') % {'max': max_size_mb},
            code='image_too_large'
        )


def validate_document_size(value):
    """
    Validate document file size (max 10MB).
    """
    max_size_mb = 10
    if value.size > max_size_mb * 1024 * 1024:
        raise ValidationError(
            _('La taille du document ne doit pas dépasser %(max)s MB.') % {'max': max_size_mb},
            code='document_too_large'
        )


def validate_pdf_file(value):
    """
    Validate that uploaded file is a PDF.
    """
    if not value.name.lower().endswith('.pdf'):
        raise ValidationError(
            _('Seuls les fichiers PDF sont acceptés.'),
            code='invalid_pdf'
        )
    
    validate_document_size(value)


# Date Validators
# ============================================================================

def validate_future_date(value):
    """
    Validate that date is in the future.
    """
    from django.utils import timezone
    
    if value <= timezone.now().date():
        raise ValidationError(
            _('La date doit être dans le futur.'),
            code='invalid_future_date'
        )


def validate_past_date(value):
    """
    Validate that date is in the past.
    """
    from django.utils import timezone
    
    if value >= timezone.now().date():
        raise ValidationError(
            _('La date doit être dans le passé.'),
            code='invalid_past_date'
        )


def validate_age(birth_date):
    """
    Validate that person is at least 18 years old.
    """
    from django.utils import timezone
    from datetime import timedelta
    
    today = timezone.now().date()
    age = (today - birth_date).days / 365.25
    
    if age < 18:
        raise ValidationError(
            _('Vous devez avoir au moins 18 ans.'),
            code='underage'
        )
    
    if age > 120:
        raise ValidationError(
            _('Date de naissance invalide.'),
            code='invalid_birth_date'
        )


# QR Code Validator
# ============================================================================

def validate_qr_code_format(value):
    """
    Validate QR code format for health tickets.
    Format: KALPE-TICKET-{UUID}
    """
    pattern = r'^KALPE-TICKET-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    if not re.match(pattern, value, re.IGNORECASE):
        raise ValidationError(
            _('Format de QR code invalide.'),
            code='invalid_qr_code'
        )


# Password Validator
# ============================================================================

class ComplexityPasswordValidator:
    """
    Validate password complexity for health data security.
    Requirements:
    - At least 12 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    
    def validate(self, password, user=None):
        if len(password) < 12:
            raise ValidationError(
                _('Le mot de passe doit contenir au moins 12 caractères.'),
                code='password_too_short',
            )
        
        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                _('Le mot de passe doit contenir au moins une lettre majuscule.'),
                code='password_no_upper',
            )
        
        if not re.search(r'[a-z]', password):
            raise ValidationError(
                _('Le mot de passe doit contenir au moins une lettre minuscule.'),
                code='password_no_lower',
            )
        
        if not re.search(r'\d', password):
            raise ValidationError(
                _('Le mot de passe doit contenir au moins un chiffre.'),
                code='password_no_digit',
            )
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError(
                _('Le mot de passe doit contenir au moins un caractère spécial.'),
                code='password_no_symbol',
            )
    
    def get_help_text(self):
        return _(
            'Votre mot de passe doit contenir au moins 12 caractères, '
            'incluant majuscules, minuscules, chiffres et caractères spéciaux.'
        )


# Medical Data Validators
# ============================================================================

def validate_blood_type(value):
    """
    Validate blood type format.
    """
    valid_types = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    if value not in valid_types:
        raise ValidationError(
            _('Groupe sanguin invalide. Valeurs acceptées: %(types)s') % {
                'types': ', '.join(valid_types)
            },
            code='invalid_blood_type'
        )


def validate_weight(value):
    """
    Validate weight in kg (realistic range: 1-300 kg).
    """
    if not (1 <= value <= 300):
        raise ValidationError(
            _('Poids invalide. Doit être entre 1 et 300 kg.'),
            code='invalid_weight'
        )


def validate_height(value):
    """
    Validate height in cm (realistic range: 30-250 cm).
    """
    if not (30 <= value <= 250):
        raise ValidationError(
            _('Taille invalide. Doit être entre 30 et 250 cm.'),
            code='invalid_height'
        )


# Geolocation Validators
# ============================================================================

def validate_latitude(value):
    """
    Validate latitude coordinates.
    """
    if not (-90 <= value <= 90):
        raise ValidationError(
            _('Latitude invalide. Doit être entre -90 et 90.'),
            code='invalid_latitude'
        )


def validate_longitude(value):
    """
    Validate longitude coordinates.
    """
    if not (-180 <= value <= 180):
        raise ValidationError(
            _('Longitude invalide. Doit être entre -180 et 180.'),
            code='invalid_longitude'
        )




