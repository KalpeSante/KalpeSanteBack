"""
KALPÉ SANTÉ - Healthcare Serializers
Serializers for healthcare API endpoints.
"""

from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from .models import (
    HealthcareProvider,
    HealthTicket,
    MedicalRecord,
    Prescription,
    PrescriptionMedication,
)
from apps.users.serializers import UserSerializer
from apps.wallet.serializers import TransactionSerializer


class HealthcareProviderSerializer(serializers.ModelSerializer):
    """Serializer for HealthcareProvider model."""
    
    user = UserSerializer(read_only=True)
    distance = serializers.SerializerMethodField()
    
    class Meta:
        model = HealthcareProvider
        fields = [
            'id', 'user', 'name', 'provider_type', 'registration_number',
            'license_number', 'phone', 'email', 'website',
            'ligne1', 'ligne2', 'ville', 'region', 'code_postal', 'pays',
            'geo_lat', 'geo_lng', 'distance',
            'opening_hours', 'specialties', 'services',
            'rating', 'review_count', 'is_verified', 'is_accepting_patients',
            'is_cmu_partner', 'cmu_contract_number',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'rating', 'review_count', 'created_at', 'updated_at']
    
    def get_distance(self, obj):
        """Calculate distance from user (if provided in context)."""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            # TODO: Implement distance calculation based on user location
            return None
        return None


class HealthcareProviderListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for provider listing."""
    
    class Meta:
        model = HealthcareProvider
        fields = [
            'id', 'name', 'provider_type', 'phone',
            'specialties', 'rating', 'is_verified', 'is_cmu_partner'
        ]


class PrescriptionMedicationSerializer(serializers.ModelSerializer):
    """Serializer for PrescriptionMedication model."""
    
    class Meta:
        model = PrescriptionMedication
        fields = [
            'id', 'medication_name', 'dosage', 'frequency',
            'duration', 'quantity', 'instructions'
        ]


class PrescriptionSerializer(serializers.ModelSerializer):
    """Serializer for Prescription model."""
    
    medications = PrescriptionMedicationSerializer(many=True, read_only=True)
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    health_ticket_number = serializers.CharField(source='health_ticket.ticket_number', read_only=True)
    is_expired = serializers.SerializerMethodField()
    days_until_expiry = serializers.SerializerMethodField()
    
    class Meta:
        model = Prescription
        fields = [
            'id', 'prescription_number', 'health_ticket', 'health_ticket_number',
            'medical_record', 'patient', 'patient_name', 'doctor', 'doctor_name',
            'issue_date', 'expiry_date', 'is_dispensed', 'dispensed_at',
            'dispensed_by_name', 'notes', 'qr_code', 'medications',
            'is_expired', 'days_until_expiry',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'prescription_number', 'qr_code', 'is_dispensed',
            'dispensed_at', 'created_at', 'updated_at'
        ]
    
    def get_is_expired(self, obj):
        """Check if prescription is expired."""
        return obj.expiry_date < timezone.now().date()
    
    def get_days_until_expiry(self, obj):
        """Calculate days until expiry."""
        delta = obj.expiry_date - timezone.now().date()
        return delta.days


class MedicalRecordSerializer(serializers.ModelSerializer):
    """Serializer for MedicalRecord model."""
    
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    ticket_number = serializers.CharField(source='health_ticket.ticket_number', read_only=True)
    prescriptions = PrescriptionSerializer(many=True, read_only=True)
    bmi = serializers.SerializerMethodField()
    
    class Meta:
        model = MedicalRecord
        fields = [
            'id', 'patient', 'patient_name', 'health_ticket', 'ticket_number',
            'doctor', 'doctor_name', 'consultation_date', 'chief_complaint',
            'temperature', 'blood_pressure_systolic', 'blood_pressure_diastolic',
            'heart_rate', 'respiratory_rate', 'weight', 'height', 'bmi',
            'physical_examination', 'diagnosis', 'treatment_plan',
            'clinical_notes', 'follow_up_required', 'follow_up_date',
            'follow_up_instructions', 'prescriptions',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_bmi(self, obj):
        """Calculate BMI if height and weight are available."""
        if obj.weight and obj.height:
            height_m = float(obj.height) / 100  # Convert cm to m
            bmi = float(obj.weight) / (height_m ** 2)
            return round(bmi, 2)
        return None


class HealthTicketSerializer(serializers.ModelSerializer):
    """Serializer for HealthTicket model."""
    
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    payment_transaction = TransactionSerializer(read_only=True)
    medical_records = MedicalRecordSerializer(many=True, read_only=True)
    prescriptions = PrescriptionSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    can_be_cancelled = serializers.SerializerMethodField()
    time_until_appointment = serializers.SerializerMethodField()
    
    class Meta:
        model = HealthTicket
        fields = [
            'id', 'ticket_number', 'patient', 'patient_name',
            'provider', 'provider_name', 'doctor', 'doctor_name',
            'appointment_date', 'specialty', 'consultation_type',
            'status', 'status_display', 'priority', 'priority_display',
            'reason', 'symptoms', 'consultation_fee', 'cmu_coverage',
            'patient_payment', 'payment_transaction', 'qr_code',
            'paid_at', 'checked_in_at', 'consultation_started_at',
            'consultation_ended_at', 'completed_at', 'cancelled_at',
            'cancellation_reason', 'staff_notes',
            'medical_records', 'prescriptions',
            'can_be_cancelled', 'time_until_appointment',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'ticket_number', 'status', 'qr_code',
            'paid_at', 'checked_in_at', 'consultation_started_at',
            'consultation_ended_at', 'completed_at', 'cancelled_at',
            'created_at', 'updated_at'
        ]
    
    def get_can_be_cancelled(self, obj):
        """Check if ticket can be cancelled."""
        return obj.can_cancel()
    
    def get_time_until_appointment(self, obj):
        """Calculate time until appointment."""
        if obj.appointment_date > timezone.now():
            delta = obj.appointment_date - timezone.now()
            hours = delta.total_seconds() / 3600
            return {
                'hours': int(hours),
                'days': delta.days,
                'is_upcoming': True
            }
        return {
            'hours': 0,
            'days': 0,
            'is_upcoming': False
        }


class HealthTicketListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for ticket listing."""
    
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = HealthTicket
        fields = [
            'id', 'ticket_number', 'patient_name', 'provider_name',
            'appointment_date', 'status', 'status_display', 'priority',
            'consultation_fee', 'created_at'
        ]


class CreateHealthTicketSerializer(serializers.Serializer):
    """Serializer for creating a health ticket."""
    
    provider_id = serializers.UUIDField(required=True)
    appointment_date = serializers.DateTimeField(required=True)
    specialty = serializers.CharField(max_length=100, required=True)
    consultation_type = serializers.ChoiceField(
        choices=['general', 'specialist', 'followup', 'emergency'],
        default='general'
    )
    priority = serializers.ChoiceField(
        choices=['normal', 'urgent', 'emergency'],
        default='normal'
    )
    reason = serializers.CharField(required=True)
    symptoms = serializers.CharField(required=False, allow_blank=True)
    
    def validate_provider_id(self, value):
        """Validate provider exists and is accepting patients."""
        try:
            provider = HealthcareProvider.objects.get(id=value)
            if not provider.is_verified:
                raise serializers.ValidationError("Provider is not verified")
            if not provider.is_accepting_patients:
                raise serializers.ValidationError("Provider is not accepting patients")
        except HealthcareProvider.DoesNotExist:
            raise serializers.ValidationError("Provider not found")
        return value
    
    def validate_appointment_date(self, value):
        """Validate appointment date is in the future."""
        if value <= timezone.now():
            raise serializers.ValidationError("Appointment date must be in the future")
        
        # Check if not too far in the future (e.g., 90 days)
        if value > timezone.now() + timedelta(days=90):
            raise serializers.ValidationError("Appointment date cannot be more than 90 days in the future")
        
        return value


class UpdateHealthTicketStatusSerializer(serializers.Serializer):
    """Serializer for updating health ticket status."""
    
    action = serializers.ChoiceField(
        choices=['check_in', 'start_consultation', 'complete_consultation', 'complete', 'cancel'],
        required=True
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    cancellation_reason = serializers.CharField(required=False, allow_blank=True)


class CreateMedicalRecordSerializer(serializers.ModelSerializer):
    """Serializer for creating a medical record."""
    
    class Meta:
        model = MedicalRecord
        fields = [
            'health_ticket', 'chief_complaint',
            'temperature', 'blood_pressure_systolic', 'blood_pressure_diastolic',
            'heart_rate', 'respiratory_rate', 'weight', 'height',
            'physical_examination', 'diagnosis', 'treatment_plan',
            'clinical_notes', 'follow_up_required', 'follow_up_date',
            'follow_up_instructions'
        ]
    
    def validate_health_ticket(self, value):
        """Validate health ticket is in consultation."""
        if value.status != HealthTicket.IN_CONSULTATION:
            raise serializers.ValidationError("Health ticket must be in consultation status")
        return value


class CreatePrescriptionSerializer(serializers.Serializer):
    """Serializer for creating a prescription with medications."""
    
    health_ticket_id = serializers.UUIDField(required=True)
    medical_record_id = serializers.UUIDField(required=True)
    expiry_days = serializers.IntegerField(default=30, min_value=1, max_value=365)
    notes = serializers.CharField(required=False, allow_blank=True)
    medications = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        required=True
    )
    
    def validate_medications(self, value):
        """Validate medications list."""
        required_fields = ['medication_name', 'dosage', 'frequency', 'duration', 'quantity']
        for med in value:
            for field in required_fields:
                if field not in med:
                    raise serializers.ValidationError(f"Missing required field: {field}")
        return value


class DispensePrescriptionSerializer(serializers.Serializer):
    """Serializer for dispensing a prescription."""
    
    pharmacy_name = serializers.CharField(max_length=200, required=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class ProviderStatisticsSerializer(serializers.Serializer):
    """Serializer for provider statistics."""
    
    total_tickets = serializers.IntegerField()
    today_appointments = serializers.IntegerField()
    in_consultation = serializers.IntegerField()
    completed_today = serializers.IntegerField()
    pending_payment = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    average_consultation_fee = serializers.DecimalField(max_digits=10, decimal_places=2)

