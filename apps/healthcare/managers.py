"""
KALPÉ SANTÉ - Healthcare Managers
Custom managers for healthcare operations.
"""

from django.db import models
from django.utils import timezone
from django.db.models import Q, Count, Avg
from datetime import timedelta


class HealthcareProviderManager(models.Manager):
    """Manager for HealthcareProvider model."""
    
    def verified(self):
        """Get verified providers."""
        return self.filter(is_verified=True, deleted_at__isnull=True)
    
    def accepting_patients(self):
        """Get providers accepting new patients."""
        return self.filter(
            is_verified=True,
            is_accepting_patients=True,
            deleted_at__isnull=True
        )
    
    def cmu_partners(self):
        """Get CMU partner providers."""
        return self.filter(is_cmu_partner=True, deleted_at__isnull=True)
    
    def by_type(self, provider_type):
        """Get providers by type."""
        return self.filter(provider_type=provider_type, deleted_at__isnull=True)
    
    def top_rated(self, limit=10):
        """Get top-rated providers."""
        return self.filter(
            is_verified=True,
            deleted_at__isnull=True
        ).order_by('-rating', '-review_count')[:limit]


class HealthTicketManager(models.Manager):
    """Manager for HealthTicket model."""
    
    def for_patient(self, patient):
        """Get tickets for specific patient."""
        return self.filter(patient=patient, deleted_at__isnull=True)
    
    def for_provider(self, provider):
        """Get tickets for specific provider."""
        return self.filter(provider=provider, deleted_at__isnull=True)
    
    def pending_payment(self):
        """Get tickets pending payment."""
        from .models import HealthTicket
        return self.filter(
            status=HealthTicket.PENDING_PAYMENT,
            deleted_at__isnull=True
        )
    
    def today_appointments(self, provider=None):
        """Get today's appointments."""
        from .models import HealthTicket
        today = timezone.now().date()
        qs = self.filter(
            appointment_date__date=today,
            status__in=[
                HealthTicket.PAID,
                HealthTicket.CHECKED_IN,
                HealthTicket.IN_CONSULTATION
            ],
            deleted_at__isnull=True
        )
        if provider:
            qs = qs.filter(provider=provider)
        return qs.order_by('appointment_date')
    
    def upcoming(self, patient=None, days=7):
        """Get upcoming appointments."""
        from .models import HealthTicket
        now = timezone.now()
        future = now + timedelta(days=days)
        qs = self.filter(
            appointment_date__gte=now,
            appointment_date__lte=future,
            status__in=[HealthTicket.PAID, HealthTicket.CREATED],
            deleted_at__isnull=True
        )
        if patient:
            qs = qs.filter(patient=patient)
        return qs.order_by('appointment_date')
    
    def in_consultation(self, provider=None):
        """Get tickets currently in consultation."""
        from .models import HealthTicket
        qs = self.filter(
            status=HealthTicket.IN_CONSULTATION,
            deleted_at__isnull=True
        )
        if provider:
            qs = qs.filter(provider=provider)
        return qs
    
    def completed_today(self, provider=None):
        """Get completed consultations today."""
        from .models import HealthTicket
        today = timezone.now().date()
        qs = self.filter(
            status__in=[HealthTicket.CONSULTATION_COMPLETED, HealthTicket.COMPLETED],
            consultation_ended_at__date=today,
            deleted_at__isnull=True
        )
        if provider:
            qs = qs.filter(provider=provider)
        return qs
    
    def by_status(self, status):
        """Get tickets by status."""
        return self.filter(status=status, deleted_at__isnull=True)
    
    def urgent(self):
        """Get urgent tickets."""
        from .models import HealthTicket
        return self.filter(
            priority__in=[HealthTicket.URGENT, HealthTicket.EMERGENCY],
            deleted_at__isnull=True
        ).order_by('-priority', 'appointment_date')
    
    def get_statistics(self, provider=None, start_date=None, end_date=None):
        """Get ticket statistics."""
        from .models import HealthTicket
        
        qs = self.filter(deleted_at__isnull=True)
        
        if provider:
            qs = qs.filter(provider=provider)
        
        if start_date:
            qs = qs.filter(created_at__gte=start_date)
        
        if end_date:
            qs = qs.filter(created_at__lte=end_date)
        
        return {
            'total': qs.count(),
            'by_status': dict(qs.values('status').annotate(count=Count('id')).values_list('status', 'count')),
            'completed': qs.filter(status=HealthTicket.COMPLETED).count(),
            'cancelled': qs.filter(status=HealthTicket.CANCELLED).count(),
            'average_fee': qs.aggregate(Avg('consultation_fee'))['consultation_fee__avg'] or 0,
        }


class MedicalRecordManager(models.Manager):
    """Manager for MedicalRecord model."""
    
    def for_patient(self, patient):
        """Get medical records for patient."""
        return self.filter(patient=patient, deleted_at__isnull=True).order_by('-consultation_date')
    
    def recent(self, patient, limit=10):
        """Get recent medical records."""
        return self.for_patient(patient)[:limit]
    
    def by_doctor(self, doctor):
        """Get records by doctor."""
        return self.filter(doctor=doctor, deleted_at__isnull=True).order_by('-consultation_date')
    
    def requiring_followup(self):
        """Get records requiring follow-up."""
        return self.filter(
            follow_up_required=True,
            follow_up_date__gte=timezone.now().date(),
            deleted_at__isnull=True
        ).order_by('follow_up_date')


class PrescriptionManager(models.Manager):
    """Manager for Prescription model."""
    
    def for_patient(self, patient):
        """Get prescriptions for patient."""
        return self.filter(patient=patient, deleted_at__isnull=True).order_by('-issue_date')
    
    def active(self, patient=None):
        """Get active (non-expired, non-dispensed) prescriptions."""
        today = timezone.now().date()
        qs = self.filter(
            is_dispensed=False,
            expiry_date__gte=today,
            deleted_at__isnull=True
        )
        if patient:
            qs = qs.filter(patient=patient)
        return qs
    
    def expired(self):
        """Get expired prescriptions."""
        today = timezone.now().date()
        return self.filter(
            expiry_date__lt=today,
            is_dispensed=False,
            deleted_at__isnull=True
        )
    
    def dispensed(self):
        """Get dispensed prescriptions."""
        return self.filter(is_dispensed=True, deleted_at__isnull=True)
    
    def by_doctor(self, doctor):
        """Get prescriptions by doctor."""
        return self.filter(doctor=doctor, deleted_at__isnull=True).order_by('-issue_date')

