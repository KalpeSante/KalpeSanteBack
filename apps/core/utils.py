"""
KALPÉ SANTÉ - Core Utilities
Reusable utility functions across the application.
"""

import hashlib
import secrets
import string
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import logging

logger = logging.getLogger('apps.core')


# String Utilities
# ============================================================================

def generate_random_string(length=32, include_punctuation=False):
    """
    Generate a cryptographically secure random string.
    
    Args:
        length: Length of the string to generate
        include_punctuation: Whether to include special characters
    
    Returns:
        Random string
    """
    alphabet = string.ascii_letters + string.digits
    if include_punctuation:
        alphabet += string.punctuation
    
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_reference_number(prefix='', length=10):
    """
    Generate a unique reference number.
    Format: PREFIX-TIMESTAMP-RANDOM
    
    Args:
        prefix: Prefix for the reference (e.g., 'TXN', 'TICKET')
        length: Length of random part
    
    Returns:
        Reference number string
    """
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    random_part = ''.join(secrets.choice(string.digits) for _ in range(length))
    
    if prefix:
        return f"{prefix}-{timestamp}-{random_part}"
    return f"{timestamp}-{random_part}"


def mask_sensitive_data(data, mask_char='*', visible_chars=4):
    """
    Mask sensitive data for logging/display.
    
    Args:
        data: Data to mask (string)
        mask_char: Character to use for masking
        visible_chars: Number of characters to leave visible at the end
    
    Returns:
        Masked string
    """
    if not data or len(data) <= visible_chars:
        return mask_char * len(data) if data else ''
    
    masked_length = len(data) - visible_chars
    return mask_char * masked_length + data[-visible_chars:]


# Hash Utilities
# ============================================================================

def calculate_sha256(data):
    """
    Calculate SHA-256 hash of data.
    
    Args:
        data: String or bytes to hash
    
    Returns:
        Hexadecimal hash string
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    return hashlib.sha256(data).hexdigest()


def verify_sha256(data, expected_hash):
    """
    Verify SHA-256 hash of data.
    
    Args:
        data: String or bytes to verify
        expected_hash: Expected hash value
    
    Returns:
        Boolean indicating if hash matches
    """
    return calculate_sha256(data) == expected_hash


# QR Code Utilities
# ============================================================================

def generate_qr_code(data, size=300):
    """
    Generate QR code image from data.
    
    Args:
        data: Data to encode in QR code
        size: Size of QR code image in pixels
    
    Returns:
        Django ContentFile containing QR code image
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Resize if needed
    if img.size[0] != size:
        img = img.resize((size, size))
    
    # Convert to bytes
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return ContentFile(buffer.getvalue(), name=f'qr_{calculate_sha256(data)[:8]}.png')


def generate_health_ticket_qr(ticket_id):
    """
    Generate QR code specifically for health tickets.
    Format: KALPE-TICKET-{UUID}
    
    Args:
        ticket_id: UUID of the health ticket
    
    Returns:
        Tuple of (qr_code_string, qr_code_image)
    """
    qr_code_string = f"KALPE-TICKET-{ticket_id}"
    qr_code_image = generate_qr_code(qr_code_string)
    
    return qr_code_string, qr_code_image


# Date/Time Utilities
# ============================================================================

def get_current_timestamp():
    """
    Get current timestamp in ISO format.
    
    Returns:
        ISO formatted timestamp string
    """
    return timezone.now().isoformat()


def add_days(days, from_date=None):
    """
    Add days to a date.
    
    Args:
        days: Number of days to add
        from_date: Starting date (defaults to now)
    
    Returns:
        New datetime object
    """
    if from_date is None:
        from_date = timezone.now()
    
    return from_date + timedelta(days=days)


def is_expired(expiration_date):
    """
    Check if a date has expired.
    
    Args:
        expiration_date: Date to check
    
    Returns:
        Boolean indicating if date is in the past
    """
    if expiration_date is None:
        return False
    
    return timezone.now() > expiration_date


# Money Utilities (XOF - Franc CFA)
# ============================================================================

def format_xof(amount):
    """
    Format amount in XOF (Franc CFA) with proper formatting.
    
    Args:
        amount: Numeric amount
    
    Returns:
        Formatted string (e.g., "1 000 500 XOF")
    """
    # Format with space as thousands separator
    formatted = f"{amount:,.0f}".replace(',', ' ')
    return f"{formatted} XOF"


def xof_to_eur(amount_xof):
    """
    Convert XOF to EUR using fixed rate (1 EUR = 655.957 XOF).
    
    Args:
        amount_xof: Amount in XOF
    
    Returns:
        Amount in EUR
    """
    return round(amount_xof / 655.957, 2)


def eur_to_xof(amount_eur):
    """
    Convert EUR to XOF using fixed rate.
    
    Args:
        amount_eur: Amount in EUR
    
    Returns:
        Amount in XOF
    """
    return round(amount_eur * 655.957, 0)


# Phone Number Utilities
# ============================================================================

def normalize_phone_number(phone):
    """
    Normalize Senegalese phone number to international format.
    
    Args:
        phone: Phone number string
    
    Returns:
        Normalized phone number (+221XXXXXXXXX)
    """
    import re
    
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Remove leading zeros
    digits = digits.lstrip('0')
    
    # Add country code if not present
    if not digits.startswith('221'):
        if len(digits) == 9:  # Local format
            digits = '221' + digits
        else:
            raise ValueError(f"Invalid phone number format: {phone}")
    
    # Ensure correct length (221 + 9 digits = 12 total)
    if len(digits) != 12:
        raise ValueError(f"Invalid phone number length: {phone}")
    
    return f"+{digits}"


def format_phone_display(phone):
    """
    Format phone number for display.
    
    Args:
        phone: Phone number string (+221XXXXXXXXX)
    
    Returns:
        Formatted phone (e.g., "+221 77 123 45 67")
    """
    normalized = normalize_phone_number(phone)
    # Format: +221 XX XXX XX XX
    return f"{normalized[:4]} {normalized[4:6]} {normalized[6:9]} {normalized[9:11]} {normalized[11:]}"


# Pagination Utilities
# ============================================================================

def get_paginated_response(queryset, serializer_class, request, page_size=20):
    """
    Helper to create paginated API responses.
    
    Args:
        queryset: Django QuerySet
        serializer_class: DRF Serializer class
        request: DRF Request object
        page_size: Items per page
    
    Returns:
        Paginated response data
    """
    from rest_framework.pagination import PageNumberPagination
    
    paginator = PageNumberPagination()
    paginator.page_size = page_size
    
    page = paginator.paginate_queryset(queryset, request)
    if page is not None:
        serializer = serializer_class(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)
    
    serializer = serializer_class(queryset, many=True, context={'request': request})
    return serializer.data


# File Utilities
# ============================================================================

def get_file_extension(filename):
    """
    Get file extension from filename.
    
    Args:
        filename: Name of the file
    
    Returns:
        File extension (lowercase, without dot)
    """
    import os
    return os.path.splitext(filename)[1][1:].lower()


def generate_unique_filename(filename, prefix=''):
    """
    Generate unique filename using timestamp and random string.
    
    Args:
        filename: Original filename
        prefix: Optional prefix
    
    Returns:
        Unique filename
    """
    import os
    from django.utils.text import slugify
    
    name, ext = os.path.splitext(filename)
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    random_str = generate_random_string(8)
    
    slug = slugify(name)[:30]  # Limit length
    
    if prefix:
        return f"{prefix}_{slug}_{timestamp}_{random_str}{ext}"
    return f"{slug}_{timestamp}_{random_str}{ext}"


# Request Utilities
# ============================================================================

def get_client_ip(request):
    """
    Extract client IP address from request.
    
    Args:
        request: Django/DRF request object
    
    Returns:
        IP address string
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request):
    """
    Extract user agent from request.
    
    Args:
        request: Django/DRF request object
    
    Returns:
        User agent string
    """
    return request.META.get('HTTP_USER_AGENT', '')


# Logging Utilities
# ============================================================================

def log_audit_event(user, action, resource_type, resource_id, ip_address, metadata=None):
    """
    Helper to log audit events.
    
    Args:
        user: User object
        action: Action type (CREATE, UPDATE, DELETE, etc.)
        resource_type: Type of resource
        resource_id: ID of resource
        ip_address: Client IP address
        metadata: Additional metadata dict
    """
    from apps.core.models import AuditLog
    
    try:
        AuditLog.objects.create(
            user=user,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent='',
            metadata=metadata or {},
        )
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")


# Validation Utilities
# ============================================================================

def is_valid_uuid(uuid_string):
    """
    Check if string is a valid UUID.
    
    Args:
        uuid_string: String to validate
    
    Returns:
        Boolean
    """
    import uuid
    try:
        uuid.UUID(str(uuid_string))
        return True
    except (ValueError, AttributeError):
        return False
