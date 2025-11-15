"""
KALPÉ SANTÉ - Healthcare Admin
Django admin configuration for healthcare models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    HealthcareProvider,
    HealthTicket,
    MedicalRecord,
    Prescription,
    PrescriptionMedication,
)


@admin.register(HealthcareProvider)
class HealthcareProviderAdmin(admin.ModelAdmin):
    """Admin interface for HealthcareProvider model."""
    
    list_display = [
        'name', 'provider_type', 'location_display', 'rating_display',
        'is_verified', 'is_cmu_partner', 'is_accepting_patients',
        'created_at'
    ]
    list_filter = [
        'provider_type', 'is_verified', 'is_cmu_partner',
        'is_accepting_patients', 'created_at'
    ]
    search_fields = ['name', 'registration_number', 'email']
    readonly_fields = ['created_at', 'updated_at', 'rating', 'review_count']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'name', 'provider_type', 'registration_number', 'license_number')
        }),
        ('Contact', {
            'fields': ('phone', 'email', 'website')
        }),
        ('Address', {
            'fields': ('ligne1', 'ligne2', 'ville', 'region', 'code_postal', 'pays', 'geo_lat', 'geo_lng')
        }),
        ('Services', {
            'fields': ('opening_hours', 'specialties', 'services')
        }),
        ('Rating', {
            'fields': ('rating', 'review_count')
        }),
        ('Status', {
            'fields': ('is_verified', 'is_accepting_patients')
        }),
        ('CMU', {
            'fields': ('is_cmu_partner', 'cmu_contract_number')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def location_display(self, obj):
        """Display city and region."""
        if obj.ville and obj.region:
            return f"{obj.ville}, {obj.region}"
        elif obj.ville:
            return obj.ville
        elif obj.region:
            return obj.region
        return "N/A"
    location_display.short_description = 'Location'
    
    def rating_display(self, obj):
        """Display rating with stars."""
        stars = '⭐' * int(obj.rating)
        return format_html(
            '<span title="{} ({} reviews)">{}</span>',
            obj.rating, obj.review_count, stars
        )
    rating_display.short_description = 'Rating'
    rating_display.admin_order_field = 'rating'
    
    actions = ['verify_providers', 'unverify_providers']
    
    def verify_providers(self, request, queryset):
        """Verify selected providers."""
        queryset.update(is_verified=True)
        self.message_user(request, f"{queryset.count()} providers verified")
    verify_providers.short_description = "Verify selected providers"
    
    def unverify_providers(self, request, queryset):
        """Unverify selected providers."""
        queryset.update(is_verified=False)
        self.message_user(request, f"{queryset.count()} providers unverified")
    unverify_providers.short_description = "Unverify selected providers"


@admin.register(HealthTicket)
class HealthTicketAdmin(admin.ModelAdmin):
    """Admin interface for HealthTicket model."""
    
    list_display = [
        'ticket_number', 'patient_name', 'provider_name',
        'appointment_date', 'status_display', 'priority_display',
        'consultation_fee', 'created_at'
    ]
    list_filter = [
        'status', 'priority', 'consultation_type',
        'appointment_date', 'created_at'
    ]
    search_fields = [
        'ticket_number', 'patient__email', 'patient__first_name',
        'patient__last_name', 'provider__name'
    ]
    readonly_fields = [
        'ticket_number', 'qr_code', 'created_at', 'updated_at',
        'paid_at', 'checked_in_at', 'consultation_started_at',
        'consultation_ended_at', 'completed_at', 'cancelled_at'
    ]
    
    fieldsets = (
        ('Ticket Info', {
            'fields': ('ticket_number', 'status', 'priority', 'qr_code')
        }),
        ('Parties', {
            'fields': ('patient', 'provider', 'doctor')
        }),
        ('Appointment', {
            'fields': ('appointment_date', 'specialty', 'consultation_type')
        }),
        ('Details', {
            'fields': ('reason', 'symptoms', 'staff_notes')
        }),
        ('Financial', {
            'fields': ('consultation_fee', 'cmu_coverage', 'patient_payment', 'payment_transaction')
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at', 'paid_at', 'checked_in_at',
                'consultation_started_at', 'consultation_ended_at',
                'completed_at', 'cancelled_at'
            ),
            'classes': ('collapse',)
        }),
        ('Cancellation', {
            'fields': ('cancellation_reason',),
            'classes': ('collapse',)
        }),
    )
    
    def patient_name(self, obj):
        return obj.patient.get_full_name()
    patient_name.short_description = 'Patient'
    patient_name.admin_order_field = 'patient__first_name'
    
    def provider_name(self, obj):
        return obj.provider.name
    provider_name.short_description = 'Provider'
    provider_name.admin_order_field = 'provider__name'
    
    def status_display(self, obj):
        """Display status with color coding."""
        colors = {
            'created': 'gray',
            'pending_payment': 'orange',
            'paid': 'green',
            'checked_in': 'blue',
            'in_consultation': 'purple',
            'consultation_completed': 'darkgreen',
            'completed': 'green',
            'cancelled': 'red',
            'refunded': 'orange',
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'
    
    def priority_display(self, obj):
        """Display priority with color."""
        colors = {
            'normal': 'green',
            'urgent': 'orange',
            'emergency': 'red',
        }
        color = colors.get(obj.priority, 'black')
        return format_html(
            '<span style="color: {};">{}</span>',
            color, obj.get_priority_display()
        )
    priority_display.short_description = 'Priority'
    priority_display.admin_order_field = 'priority'


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    """Admin interface for MedicalRecord model."""
    
    list_display = [
        'patient_name', 'doctor_name', 'consultation_date',
        'diagnosis_short', 'follow_up_required', 'created_at'
    ]
    list_filter = ['consultation_date', 'follow_up_required', 'created_at']
    search_fields = [
        'patient__email', 'patient__first_name', 'patient__last_name',
        'doctor__email', 'doctor__first_name', 'doctor__last_name',
        'diagnosis'
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('patient', 'health_ticket', 'doctor', 'consultation_date')
        }),
        ('Chief Complaint', {
            'fields': ('chief_complaint',)
        }),
        ('Vital Signs', {
            'fields': (
                'temperature', 'blood_pressure_systolic', 'blood_pressure_diastolic',
                'heart_rate', 'respiratory_rate', 'weight', 'height'
            )
        }),
        ('Clinical Findings', {
            'fields': ('physical_examination', 'diagnosis', 'treatment_plan')
        }),
        ('Notes', {
            'fields': ('clinical_notes',)
        }),
        ('Follow-up', {
            'fields': ('follow_up_required', 'follow_up_date', 'follow_up_instructions')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def patient_name(self, obj):
        return obj.patient.get_full_name()
    patient_name.short_description = 'Patient'
    
    def doctor_name(self, obj):
        return obj.doctor.get_full_name() if obj.doctor else 'N/A'
    doctor_name.short_description = 'Doctor'
    
    def diagnosis_short(self, obj):
        return obj.diagnosis[:50] + '...' if len(obj.diagnosis) > 50 else obj.diagnosis
    diagnosis_short.short_description = 'Diagnosis'


class PrescriptionMedicationInline(admin.TabularInline):
    """Inline for prescription medications."""
    model = PrescriptionMedication
    extra = 1
    fields = ['medication_name', 'dosage', 'frequency', 'duration', 'quantity', 'instructions']


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    """Admin interface for Prescription model."""
    
    list_display = [
        'prescription_number', 'patient_name', 'doctor_name',
        'issue_date', 'expiry_date', 'is_dispensed_display',
        'created_at'
    ]
    list_filter = ['is_dispensed', 'issue_date', 'expiry_date', 'created_at']
    search_fields = [
        'prescription_number', 'patient__email',
        'patient__first_name', 'patient__last_name',
        'doctor__email', 'doctor__first_name', 'doctor__last_name'
    ]
    readonly_fields = ['prescription_number', 'qr_code', 'created_at', 'updated_at']
    inlines = [PrescriptionMedicationInline]
    
    fieldsets = (
        ('Prescription Info', {
            'fields': ('prescription_number', 'qr_code')
        }),
        ('Related', {
            'fields': ('health_ticket', 'medical_record', 'patient', 'doctor')
        }),
        ('Dates', {
            'fields': ('issue_date', 'expiry_date')
        }),
        ('Dispensing', {
            'fields': ('is_dispensed', 'dispensed_at', 'dispensed_by_name')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def patient_name(self, obj):
        return obj.patient.get_full_name()
    patient_name.short_description = 'Patient'
    
    def doctor_name(self, obj):
        return obj.doctor.get_full_name()
    doctor_name.short_description = 'Doctor'
    
    def is_dispensed_display(self, obj):
        """Display dispensing status with color."""
        if obj.is_dispensed:
            return format_html('<span style="color: green;">✓ Dispensed</span>')
        elif obj.expiry_date < timezone.now().date():
            return format_html('<span style="color: red;">✗ Expired</span>')
        else:
            return format_html('<span style="color: orange;">⏳ Pending</span>')
    is_dispensed_display.short_description = 'Status'
    is_dispensed_display.admin_order_field = 'is_dispensed'


@admin.register(PrescriptionMedication)
class PrescriptionMedicationAdmin(admin.ModelAdmin):
    """Admin interface for PrescriptionMedication model."""
    
    list_display = [
        'prescription_number', 'medication_name', 'dosage',
        'frequency', 'duration', 'quantity'
    ]
    list_filter = ['created_at']
    search_fields = ['medication_name', 'prescription__prescription_number']
    
    def prescription_number(self, obj):
        return obj.prescription.prescription_number
    prescription_number.short_description = 'Prescription'
    prescription_number.admin_order_field = 'prescription__prescription_number'
