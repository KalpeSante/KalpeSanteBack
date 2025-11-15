"""
KALPÉ SANTÉ - Healthcare Models
Models for health tickets, medical records, appointments, and prescriptions.
"""

from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from apps.core.models import BaseModel, Adresse
from apps.wallet.models import Transaction
from .managers import (
    HealthcareProviderManager,
    HealthTicketManager,
    MedicalRecordManager,
    PrescriptionManager,
)
import qrcode
from io import BytesIO
from django.core.files import File


class HealthcareProvider(BaseModel, Adresse):
    """
    Healthcare facility (hospital, clinic, medical center).
    """
    # Provider Types
    HOSPITAL = 'hospital'
    CLINIC = 'clinic'
    MEDICAL_CENTER = 'medical_center'
    PHARMACY = 'pharmacy'
    LABORATORY = 'laboratory'
    
    PROVIDER_TYPES = [
        (HOSPITAL, _('Hôpital')),
        (CLINIC, _('Clinique')),
        (MEDICAL_CENTER, _('Centre Médical')),
        (PHARMACY, _('Pharmacie')),
        (LABORATORY, _('Laboratoire')),
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='healthcare_provider',
        help_text=_("Compte utilisateur du prestataire")
    )
    name = models.CharField(
        _('name'),
        max_length=200,
        help_text=_("Nom de l'établissement")
    )
    provider_type = models.CharField(
        _('provider type'),
        max_length=30,
        choices=PROVIDER_TYPES,
        db_index=True
    )
    registration_number = models.CharField(
        _('registration number'),
        max_length=50,
        unique=True,
        help_text=_("Numéro d'agrément officiel")
    )
    license_number = models.CharField(
        _('license number'),
        max_length=50,
        help_text=_("Numéro de licence d'exploitation")
    )
    phone = models.CharField(
        _('phone'),
        max_length=20
    )
    email = models.EmailField(
        _('email'),
        blank=True
    )
    website = models.URLField(
        _('website'),
        blank=True
    )
    
    # Operating hours
    opening_hours = models.JSONField(
        _('opening hours'),
        default=dict,
        blank=True,
        help_text=_("Horaires d'ouverture par jour")
    )
    
    # Specialties
    specialties = models.JSONField(
        _('specialties'),
        default=list,
        blank=True,
        help_text=_("Spécialités médicales disponibles")
    )
    
    # Services
    services = models.JSONField(
        _('services'),
        default=list,
        blank=True,
        help_text=_("Services proposés")
    )
    
    # Ratings
    rating = models.DecimalField(
        _('rating'),
        max_digits=3,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('5.00'))]
    )
    review_count = models.IntegerField(
        _('review count'),
        default=0
    )
    
    # Status
    is_verified = models.BooleanField(
        _('is verified'),
        default=False,
        help_text=_("Prestataire vérifié par l'administration")
    )
    is_accepting_patients = models.BooleanField(
        _('is accepting patients'),
        default=True
    )
    
    # CMU Integration
    is_cmu_partner = models.BooleanField(
        _('is CMU partner'),
        default=False,
        help_text=_("Conventionné avec la CMU")
    )
    cmu_contract_number = models.CharField(
        _('CMU contract number'),
        max_length=50,
        blank=True
    )
    
    objects = HealthcareProviderManager()
    
    class Meta:
        db_table = 'healthcare_providers'
        verbose_name = _('Healthcare Provider')
        verbose_name_plural = _('Healthcare Providers')
        indexes = [
            models.Index(fields=['provider_type', 'is_verified']),
            models.Index(fields=['is_cmu_partner']),
            models.Index(fields=['rating']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_provider_type_display()})"


class HealthTicket(BaseModel):
    """
    Health ticket (billet de santé) for medical consultations.
    Central entity linking patient, provider, and payment.
    """
    # Ticket Status
    CREATED = 'created'
    PENDING_PAYMENT = 'pending_payment'
    PAID = 'paid'
    CHECKED_IN = 'checked_in'
    IN_CONSULTATION = 'in_consultation'
    CONSULTATION_COMPLETED = 'consultation_completed'
    PRESCRIPTION_ISSUED = 'prescription_issued'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    REFUNDED = 'refunded'
    
    STATUS_CHOICES = [
        (CREATED, _('Créé')),
        (PENDING_PAYMENT, _('En attente de paiement')),
        (PAID, _('Payé')),
        (CHECKED_IN, _('Enregistré à l\'accueil')),
        (IN_CONSULTATION, _('En consultation')),
        (CONSULTATION_COMPLETED, _('Consultation terminée')),
        (PRESCRIPTION_ISSUED, _('Ordonnance émise')),
        (COMPLETED, _('Terminé')),
        (CANCELLED, _('Annulé')),
        (REFUNDED, _('Remboursé')),
    ]
    
    # Priority Levels
    NORMAL = 'normal'
    URGENT = 'urgent'
    EMERGENCY = 'emergency'
    
    PRIORITY_CHOICES = [
        (NORMAL, _('Normal')),
        (URGENT, _('Urgent')),
        (EMERGENCY, _('Urgence')),
    ]
    
    # Ticket reference (unique, human-readable)
    ticket_number = models.CharField(
        _('ticket number'),
        max_length=20,
        unique=True,
        db_index=True,
        help_text=_("Numéro unique du billet (ex: TS-2024-001234)")
    )
    
    # Parties involved
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='health_tickets',
        help_text=_("Patient bénéficiaire")
    )
    provider = models.ForeignKey(
        HealthcareProvider,
        on_delete=models.PROTECT,
        related_name='health_tickets',
        help_text=_("Prestataire de santé")
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consultations',
        help_text=_("Médecin traitant")
    )
    
    # Appointment details
    appointment_date = models.DateTimeField(
        _('appointment date'),
        help_text=_("Date et heure du rendez-vous")
    )
    specialty = models.CharField(
        _('specialty'),
        max_length=100,
        help_text=_("Spécialité médicale")
    )
    consultation_type = models.CharField(
        _('consultation type'),
        max_length=50,
        choices=[
            ('general', _('Consultation générale')),
            ('specialist', _('Consultation spécialisée')),
            ('followup', _('Suivi')),
            ('emergency', _('Urgence')),
        ],
        default='general'
    )
    
    # Status and priority
    status = models.CharField(
        _('status'),
        max_length=30,
        choices=STATUS_CHOICES,
        default=CREATED,
        db_index=True
    )
    priority = models.CharField(
        _('priority'),
        max_length=20,
        choices=PRIORITY_CHOICES,
        default=NORMAL
    )
    
    # Patient information
    reason = models.TextField(
        _('reason for visit'),
        help_text=_("Motif de consultation")
    )
    symptoms = models.TextField(
        _('symptoms'),
        blank=True,
        help_text=_("Symptômes décrits par le patient")
    )
    
    # Financial
    consultation_fee = models.DecimalField(
        _('consultation fee'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    cmu_coverage = models.DecimalField(
        _('CMU coverage'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Montant pris en charge par la CMU")
    )
    patient_payment = models.DecimalField(
        _('patient payment'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Montant payé par le patient")
    )
    payment_transaction = models.ForeignKey(
        Transaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='health_tickets'
    )
    
    # QR Code for verification
    qr_code = models.ImageField(
        _('QR code'),
        upload_to='health_tickets/qr_codes/',
        blank=True,
        help_text=_("QR code pour vérification rapide")
    )
    
    # Timestamps
    paid_at = models.DateTimeField(
        _('paid at'),
        null=True,
        blank=True
    )
    checked_in_at = models.DateTimeField(
        _('checked in at'),
        null=True,
        blank=True
    )
    consultation_started_at = models.DateTimeField(
        _('consultation started at'),
        null=True,
        blank=True
    )
    consultation_ended_at = models.DateTimeField(
        _('consultation ended at'),
        null=True,
        blank=True
    )
    completed_at = models.DateTimeField(
        _('completed at'),
        null=True,
        blank=True
    )
    cancelled_at = models.DateTimeField(
        _('cancelled at'),
        null=True,
        blank=True
    )
    cancellation_reason = models.TextField(
        _('cancellation reason'),
        blank=True
    )
    
    # Notes
    staff_notes = models.TextField(
        _('staff notes'),
        blank=True,
        help_text=_("Notes internes du personnel médical")
    )
    
    objects = HealthTicketManager()
    
    class Meta:
        db_table = 'health_tickets'
        verbose_name = _('Health Ticket')
        verbose_name_plural = _('Health Tickets')
        ordering = ['-appointment_date']
        indexes = [
            models.Index(fields=['ticket_number']),
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['provider', 'appointment_date']),
            models.Index(fields=['status', 'appointment_date']),
            models.Index(fields=['priority']),
        ]
    
    def __str__(self):
        return f"{self.ticket_number} - {self.patient.get_full_name()} @ {self.provider.name}"
    
    def save(self, *args, **kwargs):
        """Generate ticket number and QR code if not exists."""
        if not self.ticket_number:
            self.ticket_number = self.generate_ticket_number()
        
        super().save(*args, **kwargs)
        
        # Generate QR code after saving (need ID)
        if not self.qr_code:
            self.generate_qr_code()
    
    @staticmethod
    def generate_ticket_number():
        """Generate unique ticket number."""
        from django.utils.crypto import get_random_string
        timestamp = timezone.now().strftime('%Y%m%d')
        random_str = get_random_string(6, allowed_chars='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        return f"TS-{timestamp}-{random_str}"
    
    def generate_qr_code(self):
        """Generate QR code for ticket verification."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        # QR code data
        qr_data = {
            'ticket_id': str(self.id),
            'ticket_number': self.ticket_number,
            'patient_name': self.patient.get_full_name(),
            'provider': self.provider.name,
            'appointment_date': self.appointment_date.isoformat(),
        }
        
        qr.add_data(str(qr_data))
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to file
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        file_name = f'ticket_{self.ticket_number}.png'
        
        self.qr_code.save(file_name, File(buffer), save=True)
    
    def can_cancel(self):
        """Check if ticket can be cancelled."""
        return self.status in [self.CREATED, self.PENDING_PAYMENT, self.PAID]
    
    def cancel(self, reason=''):
        """Cancel the ticket."""
        if not self.can_cancel():
            raise ValueError(f"Cannot cancel ticket in status: {self.status}")
        
        self.status = self.CANCELLED
        self.cancelled_at = timezone.now()
        self.cancellation_reason = reason
        self.save(update_fields=['status', 'cancelled_at', 'cancellation_reason', 'updated_at'])
    
    def check_in(self):
        """Mark patient as checked in."""
        if self.status != self.PAID:
            raise ValueError("Ticket must be paid before check-in")
        
        self.status = self.CHECKED_IN
        self.checked_in_at = timezone.now()
        self.save(update_fields=['status', 'checked_in_at', 'updated_at'])
    
    def start_consultation(self):
        """Start consultation."""
        if self.status != self.CHECKED_IN:
            raise ValueError("Patient must be checked in")
        
        self.status = self.IN_CONSULTATION
        self.consultation_started_at = timezone.now()
        self.save(update_fields=['status', 'consultation_started_at', 'updated_at'])
    
    def complete_consultation(self):
        """Complete consultation."""
        if self.status != self.IN_CONSULTATION:
            raise ValueError("Consultation must be in progress")
        
        self.status = self.CONSULTATION_COMPLETED
        self.consultation_ended_at = timezone.now()
        self.save(update_fields=['status', 'consultation_ended_at', 'updated_at'])
    
    def complete(self):
        """Mark ticket as fully completed."""
        self.status = self.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at', 'updated_at'])


class MedicalRecord(BaseModel):
    """
    Electronic Medical Record (EMR) for a patient.
    """
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='medical_records'
    )
    health_ticket = models.ForeignKey(
        HealthTicket,
        on_delete=models.PROTECT,
        related_name='medical_records'
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_consultations'
    )
    
    # Consultation details
    consultation_date = models.DateTimeField(
        _('consultation date'),
        default=timezone.now
    )
    chief_complaint = models.TextField(
        _('chief complaint'),
        help_text=_("Motif principal de consultation")
    )
    
    # Vital signs
    temperature = models.DecimalField(
        _('temperature (°C)'),
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True
    )
    blood_pressure_systolic = models.IntegerField(
        _('blood pressure systolic'),
        null=True,
        blank=True
    )
    blood_pressure_diastolic = models.IntegerField(
        _('blood pressure diastolic'),
        null=True,
        blank=True
    )
    heart_rate = models.IntegerField(
        _('heart rate (bpm)'),
        null=True,
        blank=True
    )
    respiratory_rate = models.IntegerField(
        _('respiratory rate'),
        null=True,
        blank=True
    )
    weight = models.DecimalField(
        _('weight (kg)'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    height = models.DecimalField(
        _('height (cm)'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Clinical findings
    physical_examination = models.TextField(
        _('physical examination'),
        blank=True
    )
    diagnosis = models.TextField(
        _('diagnosis'),
        help_text=_("Diagnostic médical")
    )
    treatment_plan = models.TextField(
        _('treatment plan'),
        help_text=_("Plan de traitement")
    )
    
    # Additional notes
    clinical_notes = models.TextField(
        _('clinical notes'),
        blank=True
    )
    
    # Follow-up
    follow_up_required = models.BooleanField(
        _('follow-up required'),
        default=False
    )
    follow_up_date = models.DateField(
        _('follow-up date'),
        null=True,
        blank=True
    )
    follow_up_instructions = models.TextField(
        _('follow-up instructions'),
        blank=True
    )
    
    objects = MedicalRecordManager()
    
    class Meta:
        db_table = 'medical_records'
        verbose_name = _('Medical Record')
        verbose_name_plural = _('Medical Records')
        ordering = ['-consultation_date']
        indexes = [
            models.Index(fields=['patient', '-consultation_date']),
            models.Index(fields=['health_ticket']),
            models.Index(fields=['doctor']),
        ]
    
    def __str__(self):
        return f"Record for {self.patient.get_full_name()} - {self.consultation_date.date()}"


class Prescription(BaseModel):
    """
    Medical prescription issued by doctor.
    """
    prescription_number = models.CharField(
        _('prescription number'),
        max_length=20,
        unique=True,
        db_index=True
    )
    health_ticket = models.ForeignKey(
        HealthTicket,
        on_delete=models.PROTECT,
        related_name='prescriptions'
    )
    medical_record = models.ForeignKey(
        MedicalRecord,
        on_delete=models.PROTECT,
        related_name='prescriptions'
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='prescriptions'
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='issued_prescriptions'
    )
    
    # Prescription details
    issue_date = models.DateTimeField(
        _('issue date'),
        default=timezone.now
    )
    expiry_date = models.DateField(
        _('expiry date'),
        help_text=_("Date d'expiration de l'ordonnance")
    )
    
    # Status
    is_dispensed = models.BooleanField(
        _('is dispensed'),
        default=False,
        help_text=_("Médicaments délivrés en pharmacie")
    )
    dispensed_at = models.DateTimeField(
        _('dispensed at'),
        null=True,
        blank=True
    )
    # Pharmacy that dispensed the prescription (to be implemented later)
    # dispensed_by = models.ForeignKey(
    #     'pharmacy.Pharmacy',
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     related_name='dispensed_prescriptions'
    # )
    dispensed_by_name = models.CharField(
        _('dispensed by pharmacy'),
        max_length=200,
        blank=True,
        help_text=_("Nom de la pharmacie ayant délivré l'ordonnance")
    )
    
    # Notes
    notes = models.TextField(
        _('notes'),
        blank=True
    )
    
    # QR Code
    qr_code = models.ImageField(
        _('QR code'),
        upload_to='prescriptions/qr_codes/',
        blank=True
    )
    
    objects = PrescriptionManager()
    
    class Meta:
        db_table = 'prescriptions'
        verbose_name = _('Prescription')
        verbose_name_plural = _('Prescriptions')
        ordering = ['-issue_date']
        indexes = [
            models.Index(fields=['prescription_number']),
            models.Index(fields=['patient', '-issue_date']),
            models.Index(fields=['is_dispensed']),
        ]
    
    def __str__(self):
        return f"{self.prescription_number} - {self.patient.get_full_name()}"
    
    def save(self, *args, **kwargs):
        """Generate prescription number if not exists."""
        if not self.prescription_number:
            self.prescription_number = self.generate_prescription_number()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_prescription_number():
        """Generate unique prescription number."""
        from django.utils.crypto import get_random_string
        timestamp = timezone.now().strftime('%Y%m%d')
        random_str = get_random_string(6, allowed_chars='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        return f"RX-{timestamp}-{random_str}"


class PrescriptionMedication(BaseModel):
    """
    Individual medication in a prescription.
    """
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name='medications'
    )
    medication_name = models.CharField(
        _('medication name'),
        max_length=200
    )
    dosage = models.CharField(
        _('dosage'),
        max_length=100,
        help_text=_("ex: 500mg")
    )
    frequency = models.CharField(
        _('frequency'),
        max_length=200,
        help_text=_("ex: 2 fois par jour")
    )
    duration = models.CharField(
        _('duration'),
        max_length=100,
        help_text=_("ex: 7 jours")
    )
    quantity = models.IntegerField(
        _('quantity'),
        help_text=_("Nombre de boîtes/flacons")
    )
    instructions = models.TextField(
        _('instructions'),
        blank=True,
        help_text=_("Instructions spécifiques")
    )
    
    class Meta:
        db_table = 'prescription_medications'
        verbose_name = _('Prescription Medication')
        verbose_name_plural = _('Prescription Medications')
    
    def __str__(self):
        return f"{self.medication_name} - {self.dosage}"
