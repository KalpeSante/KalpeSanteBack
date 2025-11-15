"""
KALPÉ SANTÉ - User Models
Custom user model with multi-role support, MFA, KYC, and verification.
"""

import uuid
import pyotp
import secrets
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from apps.core.models import BaseModel, TimestampedModel, UUIDModel
from apps.core.validators import (
    validate_senegal_phone,
    validate_nin,
    validate_blood_type,
    validate_age,
)


class UserManager(BaseUserManager):
    """
    Custom user manager for email-based authentication.
    """
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user."""
        if not email:
            raise ValueError(_('L\'adresse email est obligatoire'))
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('email_verified', True)
        extra_fields.setdefault('phone_verified', True)
        extra_fields.setdefault('user_type', 'admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser doit avoir is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser doit avoir is_superuser=True.'))
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser, BaseModel):
    """
    Custom user model with multi-role support.
    
    Features:
    - Email-based authentication
    - Multi-role system (beneficiary, sponsor, healthcare_provider, etc.)
    - Email and phone verification
    - KYC (Know Your Customer) verification
    - MFA/2FA support
    - Security features (failed login tracking, password reset)
    """
    
    # User Types (Roles)
    BENEFICIARY = 'beneficiary'
    SPONSOR = 'sponsor'
    HEALTHCARE_PROVIDER = 'healthcare_provider'
    PHARMACIST = 'pharmacist'
    CMU_AGENT = 'cmu_agent'
    ADMIN = 'admin'
    
    USER_TYPE_CHOICES = [
        (BENEFICIARY, _('Bénéficiaire (Patient)')),
        (SPONSOR, _('Souscripteur/Parrain (Diaspora)')),
        (HEALTHCARE_PROVIDER, _('Établissement de Santé')),
        (PHARMACIST, _('Pharmacien')),
        (CMU_AGENT, _('Agent CMU/Mutuelle')),
        (ADMIN, _('Administrateur Système')),
    ]
    
    # Override default fields
    username = None  # We don't use username, only email
    email = models.EmailField(
        _('email'),
        unique=True,
        db_index=True,
        help_text=_("Adresse email unique pour connexion")
    )
    
    # Basic Information
    first_name = models.CharField(
        _('first name'),
        max_length=150,
        help_text=_("Prénom")
    )
    last_name = models.CharField(
        _('last name'),
        max_length=150,
        help_text=_("Nom de famille")
    )
    phone = models.CharField(
        _('phone number'),
        max_length=20,
        unique=True,
        db_index=True,
        validators=[validate_senegal_phone],
        help_text=_("Numéro de téléphone sénégalais (+221XXXXXXXXX)")
    )
    date_of_birth = models.DateField(
        _('date of birth'),
        null=True,
        blank=True,
        validators=[validate_age],
        help_text=_("Date de naissance (18+ ans requis)")
    )
    
    # User Type & Role
    user_type = models.CharField(
        _('user type'),
        max_length=30,
        choices=USER_TYPE_CHOICES,
        db_index=True,
        help_text=_("Rôle de l'utilisateur dans le système")
    )
    
    # Verification Status
    email_verified = models.BooleanField(
        _('email verified'),
        default=False,
        db_index=True,
        help_text=_("Email vérifié")
    )
    email_verified_at = models.DateTimeField(
        _('email verified at'),
        null=True,
        blank=True
    )
    phone_verified = models.BooleanField(
        _('phone verified'),
        default=False,
        db_index=True,
        help_text=_("Téléphone vérifié")
    )
    phone_verified_at = models.DateTimeField(
        _('phone verified at'),
        null=True,
        blank=True
    )
    
    # KYC (Know Your Customer)
    kyc_verified = models.BooleanField(
        _('KYC verified'),
        default=False,
        db_index=True,
        help_text=_("Vérification d'identité complétée")
    )
    kyc_verified_at = models.DateTimeField(
        _('KYC verified at'),
        null=True,
        blank=True
    )
    kyc_level = models.IntegerField(
        _('KYC level'),
        default=0,
        choices=[(0, 'Non vérifié'), (1, 'Basique'), (2, 'Complet'), (3, 'Avancé')],
        help_text=_("Niveau de vérification KYC")
    )
    
    # MFA/2FA
    mfa_enabled = models.BooleanField(
        _('MFA enabled'),
        default=False,
        help_text=_("Authentification à deux facteurs activée")
    )
    mfa_secret = models.CharField(
        _('MFA secret'),
        max_length=32,
        blank=True,
        help_text=_("Secret TOTP pour MFA")
    )
    backup_codes = models.JSONField(
        _('backup codes'),
        default=list,
        blank=True,
        help_text=_("Codes de secours MFA")
    )
    
    # Security
    failed_login_attempts = models.IntegerField(
        _('failed login attempts'),
        default=0,
        help_text=_("Nombre de tentatives de connexion échouées")
    )
    locked_until = models.DateTimeField(
        _('locked until'),
        null=True,
        blank=True,
        help_text=_("Date de fin de verrouillage du compte")
    )
    last_login_ip = models.GenericIPAddressField(
        _('last login IP'),
        null=True,
        blank=True,
        help_text=_("Dernière adresse IP de connexion")
    )
    password_changed_at = models.DateTimeField(
        _('password changed at'),
        null=True,
        blank=True,
        help_text=_("Date du dernier changement de mot de passe")
    )
    
    # Profile
    avatar = models.ImageField(
        _('avatar'),
        upload_to='avatars/%Y/%m/',
        null=True,
        blank=True,
        help_text=_("Photo de profil")
    )
    bio = models.TextField(
        _('bio'),
        blank=True,
        max_length=500,
        help_text=_("Biographie courte")
    )
    language = models.CharField(
        _('language'),
        max_length=10,
        default='fr',
        choices=[('fr', 'Français'), ('en', 'English'), ('wo', 'Wolof')],
        help_text=_("Langue préférée")
    )
    timezone = models.CharField(
        _('timezone'),
        max_length=50,
        default='Africa/Dakar',
        help_text=_("Fuseau horaire")
    )
    
    # Metadata
    onboarding_completed = models.BooleanField(
        _('onboarding completed'),
        default=False,
        help_text=_("Processus d'onboarding terminé")
    )
    terms_accepted_at = models.DateTimeField(
        _('terms accepted at'),
        null=True,
        blank=True,
        help_text=_("Date d'acceptation des CGU")
    )
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'phone', 'user_type']
    
    class Meta:
        db_table = 'users'
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
            models.Index(fields=['user_type']),
            models.Index(fields=['email_verified', 'phone_verified']),
            models.Index(fields=['kyc_verified']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"
    
    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name
    
    @property
    def age(self):
        """Calculate user age from date_of_birth."""
        if self.date_of_birth:
            today = timezone.now().date()
            return (today - self.date_of_birth).days // 365
        return None
    
    @property
    def is_fully_verified(self):
        """Check if user is fully verified (email + phone + KYC)."""
        return self.email_verified and self.phone_verified and self.kyc_verified
    
    @property
    def is_account_locked(self):
        """Check if account is currently locked."""
        if self.locked_until:
            return timezone.now() < self.locked_until
        return False
    
    def verify_email(self):
        """Mark email as verified."""
        self.email_verified = True
        self.email_verified_at = timezone.now()
        self.save(update_fields=['email_verified', 'email_verified_at', 'updated_at'])
    
    def verify_phone(self):
        """Mark phone as verified."""
        self.phone_verified = True
        self.phone_verified_at = timezone.now()
        self.save(update_fields=['phone_verified', 'phone_verified_at', 'updated_at'])
    
    def complete_kyc(self, level=1):
        """Mark KYC as completed."""
        self.kyc_verified = True
        self.kyc_verified_at = timezone.now()
        self.kyc_level = level
        self.save(update_fields=['kyc_verified', 'kyc_verified_at', 'kyc_level', 'updated_at'])
    
    def enable_mfa(self):
        """Enable MFA and generate secret."""
        if not self.mfa_secret:
            self.mfa_secret = pyotp.random_base32()
        self.mfa_enabled = True
        self.backup_codes = self._generate_backup_codes()
        self.save(update_fields=['mfa_enabled', 'mfa_secret', 'backup_codes', 'updated_at'])
        return self.mfa_secret
    
    def disable_mfa(self):
        """Disable MFA."""
        self.mfa_enabled = False
        self.save(update_fields=['mfa_enabled', 'updated_at'])
    
    def get_totp_uri(self):
        """Get TOTP URI for QR code generation."""
        if not self.mfa_secret:
            self.mfa_secret = pyotp.random_base32()
            self.save(update_fields=['mfa_secret'])
        
        return pyotp.totp.TOTP(self.mfa_secret).provisioning_uri(
            name=self.email,
            issuer_name='KALPÉ SANTÉ'
        )
    
    def verify_totp(self, token):
        """Verify TOTP token."""
        if not self.mfa_enabled or not self.mfa_secret:
            return False
        
        totp = pyotp.TOTP(self.mfa_secret)
        return totp.verify(token, valid_window=1)
    
    def verify_backup_code(self, code):
        """Verify and consume backup code."""
        if code in self.backup_codes:
            self.backup_codes.remove(code)
            self.save(update_fields=['backup_codes', 'updated_at'])
            return True
        return False
    
    def _generate_backup_codes(self, count=10):
        """Generate backup codes for MFA."""
        return [secrets.token_hex(4).upper() for _ in range(count)]
    
    def lock_account(self, duration_minutes=30):
        """Lock account after failed login attempts."""
        self.locked_until = timezone.now() + timezone.timedelta(minutes=duration_minutes)
        self.save(update_fields=['locked_until', 'updated_at'])
    
    def unlock_account(self):
        """Unlock account manually."""
        self.locked_until = None
        self.failed_login_attempts = 0
        self.save(update_fields=['locked_until', 'failed_login_attempts', 'updated_at'])
    
    def record_failed_login(self):
        """Record failed login attempt."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.lock_account()
        self.save(update_fields=['failed_login_attempts', 'updated_at'])
    
    def record_successful_login(self, ip_address=None):
        """Record successful login."""
        self.failed_login_attempts = 0
        self.last_login = timezone.now()
        if ip_address:
            self.last_login_ip = ip_address
        self.save(update_fields=['failed_login_attempts', 'last_login', 'last_login_ip', 'updated_at'])


class Profile(BaseModel):
    """
    Extended user profile with health and personal information.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        unique=True
    )
    
    # National ID
    nin = models.CharField(
        _('NIN'),
        max_length=13,
        unique=True,
        null=True,
        blank=True,
        validators=[validate_nin],
        help_text=_("Numéro d'Identification National (13 chiffres)")
    )
    
    # CMU Information
    cmu_number = models.CharField(
        _('CMU number'),
        max_length=50,
        blank=True,
        db_index=True,
        help_text=_("Numéro d'adhérent CMU")
    )
    cmu_status = models.CharField(
        _('CMU status'),
        max_length=20,
        choices=[
            ('active', 'Actif'),
            ('inactive', 'Inactif'),
            ('pending', 'En attente'),
            ('suspended', 'Suspendu'),
        ],
        default='inactive',
        help_text=_("Statut de l'adhésion CMU")
    )
    
    # Health Information
    blood_type = models.CharField(
        _('blood type'),
        max_length=5,
        blank=True,
        validators=[validate_blood_type],
        help_text=_("Groupe sanguin (A+, B-, etc.)")
    )
    weight = models.DecimalField(
        _('weight'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Poids en kg")
    )
    height = models.IntegerField(
        _('height'),
        null=True,
        blank=True,
        help_text=_("Taille en cm")
    )
    allergies = models.JSONField(
        _('allergies'),
        default=list,
        blank=True,
        help_text=_("Liste des allergies connues")
    )
    medical_history = models.JSONField(
        _('medical history'),
        default=list,
        blank=True,
        help_text=_("Antécédents médicaux")
    )
    
    # Emergency Contacts
    emergency_contacts = models.JSONField(
        _('emergency contacts'),
        default=list,
        blank=True,
        help_text=_("Contacts d'urgence [{name, phone, relation}]")
    )
    
    # Address
    address_line1 = models.CharField(
        _('address line 1'),
        max_length=255,
        blank=True
    )
    address_line2 = models.CharField(
        _('address line 2'),
        max_length=255,
        blank=True
    )
    city = models.CharField(
        _('city'),
        max_length=100,
        blank=True
    )
    region = models.CharField(
        _('region'),
        max_length=100,
        blank=True
    )
    postal_code = models.CharField(
        _('postal code'),
        max_length=20,
        blank=True
    )
    country = models.CharField(
        _('country'),
        max_length=100,
        default='Sénégal'
    )
    
    # Geolocation
    latitude = models.DecimalField(
        _('latitude'),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    longitude = models.DecimalField(
        _('longitude'),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    
    # Preferences
    notifications_enabled = models.BooleanField(
        _('notifications enabled'),
        default=True
    )
    email_notifications = models.BooleanField(
        _('email notifications'),
        default=True
    )
    sms_notifications = models.BooleanField(
        _('SMS notifications'),
        default=True
    )
    push_notifications = models.BooleanField(
        _('push notifications'),
        default=True
    )
    
    class Meta:
        db_table = 'user_profiles'
        verbose_name = _('Profile')
        verbose_name_plural = _('Profiles')
    
    def __str__(self):
        return f"Profile of {self.user.get_full_name()}"
    
    @property
    def full_address(self):
        """Return formatted full address."""
        parts = [self.address_line1]
        if self.address_line2:
            parts.append(self.address_line2)
        parts.extend([self.city, self.region, self.country])
        return ', '.join(filter(None, parts))
    
    @property
    def has_geolocation(self):
        """Check if geolocation coordinates are set."""
        return self.latitude is not None and self.longitude is not None


class VerificationCode(UUIDModel, TimestampedModel):
    """
    Verification codes for email and phone verification.
    """
    CODE_TYPE_CHOICES = [
        ('email', _('Email Verification')),
        ('phone', _('Phone Verification')),
        ('password_reset', _('Password Reset')),
        ('mfa_setup', _('MFA Setup')),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='verification_codes'
    )
    code_type = models.CharField(
        _('code type'),
        max_length=20,
        choices=CODE_TYPE_CHOICES
    )
    code = models.CharField(
        _('code'),
        max_length=10,
        db_index=True,
        help_text=_("Code de vérification (6 chiffres)")
    )
    is_used = models.BooleanField(
        _('is used'),
        default=False
    )
    used_at = models.DateTimeField(
        _('used at'),
        null=True,
        blank=True
    )
    expires_at = models.DateTimeField(
        _('expires at'),
        help_text=_("Date d'expiration du code")
    )
    
    class Meta:
        db_table = 'verification_codes'
        verbose_name = _('Verification Code')
        verbose_name_plural = _('Verification Codes')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'code_type', 'is_used']),
            models.Index(fields=['code', 'is_used']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.get_code_type_display()} code for {self.user.email}"
    
    @property
    def is_valid(self):
        """Check if code is still valid (not used and not expired)."""
        return not self.is_used and timezone.now() < self.expires_at
    
    def use_code(self):
        """Mark code as used."""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])
    
    @classmethod
    def generate_code(cls, user, code_type, expiry_minutes=15):
        """
        Generate a new verification code.
        
        Args:
            user: User instance
            code_type: Type of code (email, phone, password_reset)
            expiry_minutes: Minutes until expiration (default 15)
        
        Returns:
            VerificationCode instance with generated code
        """
        code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        expires_at = timezone.now() + timezone.timedelta(minutes=expiry_minutes)
        
        return cls.objects.create(
            user=user,
            code_type=code_type,
            code=code,
            expires_at=expires_at
        )


class KYCDocument(BaseModel):
    """
    KYC documents uploaded by users for identity verification.
    """
    DOCUMENT_TYPE_CHOICES = [
        ('national_id', _('Carte d\'Identité Nationale')),
        ('passport', _('Passeport')),
        ('driver_license', _('Permis de Conduire')),
        ('residence_permit', _('Carte de Séjour')),
        ('utility_bill', _('Facture de Services Publics')),
        ('selfie', _('Photo Selfie avec Document')),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('En attente')),
        ('under_review', _('En cours de vérification')),
        ('approved', _('Approuvé')),
        ('rejected', _('Rejeté')),
        ('expired', _('Expiré')),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='kyc_documents'
    )
    document_type = models.CharField(
        _('document type'),
        max_length=20,
        choices=DOCUMENT_TYPE_CHOICES
    )
    document_number = models.CharField(
        _('document number'),
        max_length=100,
        blank=True,
        help_text=_("Numéro du document")
    )
    document_file = models.FileField(
        _('document file'),
        upload_to='kyc_documents/%Y/%m/',
        help_text=_("Fichier du document (PDF, JPG, PNG)")
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_kyc_documents',
        limit_choices_to={'user_type__in': ['admin', 'cmu_agent']}
    )
    verified_at = models.DateTimeField(
        _('verified at'),
        null=True,
        blank=True
    )
    rejection_reason = models.TextField(
        _('rejection reason'),
        blank=True,
        help_text=_("Raison du rejet si applicable")
    )
    expires_at = models.DateField(
        _('expires at'),
        null=True,
        blank=True,
        help_text=_("Date d'expiration du document")
    )
    notes = models.TextField(
        _('notes'),
        blank=True,
        help_text=_("Notes internes pour la vérification")
    )
    
    class Meta:
        db_table = 'kyc_documents'
        verbose_name = _('KYC Document')
        verbose_name_plural = _('KYC Documents')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_document_type_display()} - {self.user.get_full_name()} ({self.status})"
    
    def approve(self, verified_by):
        """Approve KYC document."""
        self.status = 'approved'
        self.verified_by = verified_by
        self.verified_at = timezone.now()
        self.save(update_fields=['status', 'verified_by', 'verified_at', 'updated_at'])
    
    def reject(self, verified_by, reason):
        """Reject KYC document."""
        self.status = 'rejected'
        self.verified_by = verified_by
        self.verified_at = timezone.now()
        self.rejection_reason = reason
        self.save(update_fields=['status', 'verified_by', 'verified_at', 'rejection_reason', 'updated_at'])
    
    @property
    def is_expired(self):
        """Check if document has expired."""
        if self.expires_at:
            return timezone.now().date() > self.expires_at
        return False


class UserSession(UUIDModel, TimestampedModel):
    """
    Track user sessions for security and analytics.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    session_key = models.CharField(
        _('session key'),
        max_length=40,
        unique=True,
        db_index=True
    )
    ip_address = models.GenericIPAddressField(
        _('IP address')
    )
    user_agent = models.TextField(
        _('user agent'),
        blank=True
    )
    device_type = models.CharField(
        _('device type'),
        max_length=20,
        choices=[
            ('desktop', _('Desktop')),
            ('mobile', _('Mobile')),
            ('tablet', _('Tablet')),
            ('unknown', _('Unknown')),
        ],
        default='unknown'
    )
    browser = models.CharField(
        _('browser'),
        max_length=50,
        blank=True
    )
    os = models.CharField(
        _('operating system'),
        max_length=50,
        blank=True
    )
    country = models.CharField(
        _('country'),
        max_length=100,
        blank=True
    )
    city = models.CharField(
        _('city'),
        max_length=100,
        blank=True
    )
    is_active = models.BooleanField(
        _('is active'),
        default=True
    )
    last_activity = models.DateTimeField(
        _('last activity'),
        auto_now=True
    )
    logged_out_at = models.DateTimeField(
        _('logged out at'),
        null=True,
        blank=True
    )
    
    class Meta:
        db_table = 'user_sessions'
        verbose_name = _('User Session')
        verbose_name_plural = _('User Sessions')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['session_key']),
            models.Index(fields=['last_activity']),
        ]
    
    def __str__(self):
        return f"Session for {self.user.email} from {self.ip_address}"
    
    def logout(self):
        """Mark session as logged out."""
        self.is_active = False
        self.logged_out_at = timezone.now()
        self.save(update_fields=['is_active', 'logged_out_at'])


class LoginAttempt(UUIDModel, TimestampedModel):
    """
    Track login attempts for security monitoring.
    """
    email = models.EmailField(
        _('email'),
        db_index=True
    )
    ip_address = models.GenericIPAddressField(
        _('IP address'),
        db_index=True
    )
    user_agent = models.TextField(
        _('user agent'),
        blank=True
    )
    success = models.BooleanField(
        _('success'),
        default=False,
        db_index=True
    )
    failure_reason = models.CharField(
        _('failure reason'),
        max_length=100,
        blank=True,
        choices=[
            ('invalid_credentials', _('Invalid Credentials')),
            ('account_locked', _('Account Locked')),
            ('account_inactive', _('Account Inactive')),
            ('email_not_verified', _('Email Not Verified')),
            ('mfa_required', _('MFA Required')),
            ('mfa_failed', _('MFA Failed')),
        ]
    )
    
    class Meta:
        db_table = 'login_attempts'
        verbose_name = _('Login Attempt')
        verbose_name_plural = _('Login Attempts')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'success', '-created_at']),
            models.Index(fields=['ip_address', '-created_at']),
            models.Index(fields=['success', '-created_at']),
        ]
    
    def __str__(self):
        status = 'Success' if self.success else f'Failed ({self.failure_reason})'
        return f"{status} - {self.email} from {self.ip_address}"
    
    @classmethod
    def record_attempt(cls, email, ip_address, user_agent='', success=False, failure_reason=''):
        """Record a login attempt."""
        return cls.objects.create(
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            failure_reason=failure_reason
        )
