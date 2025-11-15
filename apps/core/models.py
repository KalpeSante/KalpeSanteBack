"""
KALPÉ SANTÉ - Core Models
Base models providing common functionality for all applications.
These models follow Django and security best practices.
"""

import uuid
import hashlib
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model


class TimestampedModel(models.Model):
    """
    Abstract base model providing automatic timestamp fields.
    All models inheriting from this will have creation and update timestamps.
    
    Fields:
        created_at: Automatically set when the object is created
        updated_at: Automatically updated when the object is modified
    """
    created_at = models.DateTimeField(
        _('created at'),
        auto_now_add=True,
        db_index=True,
        help_text=_("Date et heure de création automatique")
    )
    updated_at = models.DateTimeField(
        _('updated at'),
        auto_now=True,
        help_text=_("Date et heure de dernière modification")
    )
    
    class Meta:
        abstract = True
        ordering = ['-created_at']
        get_latest_by = 'created_at'


class SoftDeleteModel(models.Model):
    """
    Abstract model for soft delete functionality (RGPD/GDPR compliant).
    Objects are never actually deleted from the database, only marked as inactive.
    
    Fields:
        is_active: Boolean flag indicating if the object is active
        deleted_at: Timestamp when the object was soft-deleted
    """
    is_active = models.BooleanField(
        _('active'),
        default=True,
        db_index=True,
        help_text=_("Faux = suppression logique pour conformité RGPD")
    )
    deleted_at = models.DateTimeField(
        _('deleted at'),
        null=True,
        blank=True,
        help_text=_("Date de suppression logique")
    )
    
    class Meta:
        abstract = True
    
    def soft_delete(self, user=None):
        """
        Perform a soft delete on the object.
        
        Args:
            user: The user performing the deletion (for audit purposes)
        """
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_active', 'deleted_at', 'updated_at'])
        
        # Log the deletion for audit trail
        if hasattr(self, 'log_audit'):
            self.log_audit('DELETE', user=user)
    
    def restore(self, user=None):
        """
        Restore a soft-deleted object.
        
        Args:
            user: The user performing the restoration (for audit purposes)
        """
        self.is_active = True
        self.deleted_at = None
        self.save(update_fields=['is_active', 'deleted_at', 'updated_at'])
        
        # Log the restoration for audit trail
        if hasattr(self, 'log_audit'):
            self.log_audit('RESTORE', user=user)


class UUIDModel(models.Model):
    """
    Abstract model using UUID as primary key for security and distribution.
    UUID4 provides better security than sequential integer IDs.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_("Identifiant unique UUID4 pour sécurité")
    )
    
    class Meta:
        abstract = True


class BaseModel(TimestampedModel, SoftDeleteModel, UUIDModel):
    """
    Complete base model combining all common functionality:
    - UUID primary key
    - Automatic timestamps
    - Soft delete capability
    
    This model should be used as the base for all application models.
    """
    
    class Meta:
        abstract = True
    
    def __str__(self):
        """Default string representation showing UUID."""
        return f"{self.__class__.__name__}({str(self.id)[:8]}...)"


class AuditLog(UUIDModel, TimestampedModel):
    """
    Immutable audit log for compliance and security (HIPAA, RGPD).
    Records all sensitive operations with blockchain-inspired hash chaining.
    
    This provides complete traceability required for health data compliance.
    """
    # Action types
    CREATE = 'CREATE'
    READ = 'READ'
    UPDATE = 'UPDATE'
    DELETE = 'DELETE'
    ACCESS = 'ACCESS'
    LOGIN = 'LOGIN'
    LOGOUT = 'LOGOUT'
    PERMISSION_CHANGE = 'PERMISSION_CHANGE'
    
    ACTION_CHOICES = [
        (CREATE, _('Création')),
        (READ, _('Lecture')),
        (UPDATE, _('Modification')),
        (DELETE, _('Suppression')),
        (ACCESS, _('Accès')),
        (LOGIN, _('Connexion')),
        (LOGOUT, _('Déconnexion')),
        (PERMISSION_CHANGE, _('Changement de permissions')),
    ]
    
    # User who performed the action
    user = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,  # Never delete audit logs
        related_name='audit_logs',
        null=True,  # Can be null for system actions
        help_text=_("Utilisateur ayant effectué l'action")
    )
    
    # Action details
    action = models.CharField(
        _('action'),
        max_length=50,
        choices=ACTION_CHOICES,
        db_index=True,
        help_text=_("Type d'action effectuée")
    )
    
    # Resource being acted upon
    resource_type = models.CharField(
        _('resource type'),
        max_length=100,
        db_index=True,
        help_text=_("Type de ressource (Transaction, MedicalRecord, etc.)")
    )
    resource_id = models.UUIDField(
        _('resource ID'),
        db_index=True,
        help_text=_("ID de la ressource concernée")
    )
    
    # Request metadata
    ip_address = models.GenericIPAddressField(
        _('IP address'),
        help_text=_("Adresse IP de l'utilisateur")
    )
    user_agent = models.TextField(
        _('user agent'),
        blank=True,
        help_text=_("User agent du navigateur")
    )
    
    # Change details (JSON)
    changes = models.JSONField(
        _('changes'),
        default=dict,
        blank=True,
        help_text=_("Détails des modifications (avant/après)")
    )
    
    # Additional metadata
    metadata = models.JSONField(
        _('metadata'),
        default=dict,
        blank=True,
        help_text=_("Métadonnées additionnelles")
    )
    
    # Blockchain-inspired hash chaining for immutability
    previous_hash = models.CharField(
        _('previous hash'),
        max_length=64,
        blank=True,
        help_text=_("Hash de l'entrée précédente pour chaînage")
    )
    current_hash = models.CharField(
        _('current hash'),
        max_length=64,
        unique=True,
        editable=False,
        help_text=_("Hash de cette entrée")
    )
    
    class Meta:
        verbose_name = _('audit log')
        verbose_name_plural = _('audit logs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['action', '-created_at']),
            models.Index(fields=['ip_address', '-created_at']),
        ]
    
    def save(self, *args, **kwargs):
        """Override save to calculate hash before saving."""
        if not self.current_hash:
            # Get the last audit log's hash
            last_log = AuditLog.objects.order_by('-created_at').first()
            self.previous_hash = last_log.current_hash if last_log else ''
            
            # Calculate current hash
            self.current_hash = self._calculate_hash()
        
        super().save(*args, **kwargs)
    
    def _calculate_hash(self):
        """
        Calculate SHA-256 hash of this audit entry.
        Includes previous hash for chain integrity.
        """
        data = f"{self.user_id}{self.action}{self.resource_type}{self.resource_id}{self.ip_address}{self.previous_hash}{timezone.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def verify_chain(self):
        """
        Verify the integrity of the audit chain.
        Returns True if the hash chain is valid.
        """
        if not self.previous_hash:
            return True  # First entry
        
        try:
            previous_log = AuditLog.objects.filter(
                current_hash=self.previous_hash
            ).first()
            return previous_log is not None
        except AuditLog.DoesNotExist:
            return False
    
    def __str__(self):
        return f"{self.action} on {self.resource_type} by {self.user} at {self.created_at}"


class Adresse(models.Model):
    """
    Abstract model for address information.
    Used by users, healthcare facilities, pharmacies, etc.
    """
    ligne1 = models.CharField(
        _('address line 1'),
        max_length=255,
        help_text=_("Rue, numéro, bâtiment")
    )
    ligne2 = models.CharField(
        _('address line 2'),
        max_length=255,
        blank=True,
        help_text=_("Complément d'adresse (optionnel)")
    )
    ville = models.CharField(
        _('city'),
        max_length=100,
        help_text=_("Ville")
    )
    region = models.CharField(
        _('region'),
        max_length=100,
        help_text=_("Région administrative")
    )
    code_postal = models.CharField(
        _('postal code'),
        max_length=20,
        blank=True,
        help_text=_("Code postal")
    )
    pays = models.CharField(
        _('country'),
        max_length=100,
        default='Sénégal',
        help_text=_("Pays")
    )
    
    # Geolocation for mapping and distance calculations
    geo_lat = models.DecimalField(
        _('latitude'),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text=_("Latitude GPS")
    )
    geo_lng = models.DecimalField(
        _('longitude'),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text=_("Longitude GPS")
    )
    
    class Meta:
        abstract = True
        verbose_name = _('adresse')
        verbose_name_plural = _('adresses')
    
    def __str__(self):
        return f"{self.ligne1}, {self.ville}, {self.region}"
    
    @property
    def full_address(self):
        """Return complete formatted address."""
        parts = [self.ligne1]
        if self.ligne2:
            parts.append(self.ligne2)
        parts.extend([self.ville, self.region, self.pays])
        if self.code_postal:
            parts.insert(-1, self.code_postal)
        return ', '.join(parts)
    
    @property
    def has_geolocation(self):
        """Check if geolocation coordinates are available."""
        return self.geo_lat is not None and self.geo_lng is not None
