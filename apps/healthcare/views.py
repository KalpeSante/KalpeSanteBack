"""
KALPÉ SANTÉ - Healthcare Views
API endpoints for healthcare operations.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from datetime import timedelta, datetime

from .models import (
    HealthcareProvider,
    HealthTicket,
    MedicalRecord,
    Prescription,
    PrescriptionMedication,
)
from .serializers import (
    HealthcareProviderSerializer,
    HealthcareProviderListSerializer,
    HealthTicketSerializer,
    HealthTicketListSerializer,
    CreateHealthTicketSerializer,
    UpdateHealthTicketStatusSerializer,
    MedicalRecordSerializer,
    CreateMedicalRecordSerializer,
    PrescriptionSerializer,
    CreatePrescriptionSerializer,
    DispensePrescriptionSerializer,
    ProviderStatisticsSerializer,
)
from apps.core.permissions import IsOwner


@extend_schema_view(
    list=extend_schema(tags=['Healthcare Providers'], description='List healthcare providers'),
    retrieve=extend_schema(tags=['Healthcare Providers'], description='Get provider details'),
)
class HealthcareProviderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for healthcare providers.
    Patients can search and view providers.
    """
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['provider_type', 'is_verified', 'is_cmu_partner']
    search_fields = ['name', 'specialties', 'services']
    ordering_fields = ['name', 'rating', 'created_at']
    ordering = ['-rating', 'name']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return HealthcareProviderListSerializer
        return HealthcareProviderSerializer
    
    def get_queryset(self):
        """Get verified providers."""
        return HealthcareProvider.objects.verified()
    
    @extend_schema(
        tags=['Healthcare Providers'],
        description='Get providers accepting new patients'
    )
    @action(detail=False, methods=['get'])
    def accepting_patients(self, request):
        """Get providers accepting new patients."""
        providers = HealthcareProvider.objects.accepting_patients()
        serializer = self.get_serializer(providers, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Healthcare Providers'],
        description='Get CMU partner providers'
    )
    @action(detail=False, methods=['get'])
    def cmu_partners(self, request):
        """Get CMU partner providers."""
        providers = HealthcareProvider.objects.cmu_partners()
        serializer = self.get_serializer(providers, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Healthcare Providers'],
        description='Get top-rated providers'
    )
    @action(detail=False, methods=['get'])
    def top_rated(self, request):
        """Get top-rated providers."""
        limit = int(request.query_params.get('limit', 10))
        providers = HealthcareProvider.objects.top_rated(limit=limit)
        serializer = self.get_serializer(providers, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Healthcare Providers'],
        description='Get provider statistics (provider staff only)',
        responses={200: ProviderStatisticsSerializer}
    )
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get provider statistics."""
        provider = self.get_object()
        
        # Check if user is provider staff
        if request.user != provider.user and not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Calculate statistics
        tickets = HealthTicket.objects.for_provider(provider)
        today = timezone.now().date()
        
        stats = {
            'total_tickets': tickets.count(),
            'today_appointments': tickets.filter(appointment_date__date=today).count(),
            'in_consultation': tickets.filter(status=HealthTicket.IN_CONSULTATION).count(),
            'completed_today': tickets.filter(
                status__in=[HealthTicket.CONSULTATION_COMPLETED, HealthTicket.COMPLETED],
                consultation_ended_at__date=today
            ).count(),
            'pending_payment': tickets.filter(status=HealthTicket.PENDING_PAYMENT).count(),
            'cancelled': tickets.filter(status=HealthTicket.CANCELLED).count(),
            'total_revenue': tickets.filter(status__in=[
                HealthTicket.PAID, HealthTicket.CHECKED_IN,
                HealthTicket.IN_CONSULTATION, HealthTicket.CONSULTATION_COMPLETED,
                HealthTicket.COMPLETED
            ]).aggregate(Sum('consultation_fee'))['consultation_fee__sum'] or 0,
            'average_consultation_fee': tickets.aggregate(
                Avg('consultation_fee')
            )['consultation_fee__avg'] or 0,
        }
        
        serializer = ProviderStatisticsSerializer(stats)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(tags=['Health Tickets'], description='List health tickets'),
    retrieve=extend_schema(tags=['Health Tickets'], description='Get ticket details'),
    create=extend_schema(tags=['Health Tickets'], description='Create a health ticket'),
)
class HealthTicketViewSet(viewsets.ModelViewSet):
    """
    ViewSet for health tickets.
    """
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'priority', 'provider', 'appointment_date']
    search_fields = ['ticket_number', 'reason']
    ordering_fields = ['appointment_date', 'created_at', 'priority']
    ordering = ['-appointment_date']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateHealthTicketSerializer
        elif self.action == 'list':
            return HealthTicketListSerializer
        elif self.action == 'update_status':
            return UpdateHealthTicketStatusSerializer
        return HealthTicketSerializer
    
    def get_queryset(self):
        """Filter tickets based on user role."""
        user = self.request.user
        
        if user.is_staff:
            return HealthTicket.objects.all()
        
        # Provider staff can see their provider's tickets
        if hasattr(user, 'healthcare_provider'):
            return HealthTicket.objects.for_provider(user.healthcare_provider)
        
        # Patients see their own tickets
        return HealthTicket.objects.for_patient(user)
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create a new health ticket."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        provider = HealthcareProvider.objects.get(id=serializer.validated_data['provider_id'])
        
        # Create ticket
        ticket = HealthTicket.objects.create(
            patient=request.user,
            provider=provider,
            appointment_date=serializer.validated_data['appointment_date'],
            specialty=serializer.validated_data['specialty'],
            consultation_type=serializer.validated_data['consultation_type'],
            priority=serializer.validated_data['priority'],
            reason=serializer.validated_data['reason'],
            symptoms=serializer.validated_data.get('symptoms', ''),
            consultation_fee=provider.rating * 10000,  # Example pricing logic
            status=HealthTicket.PENDING_PAYMENT
        )
        
        return Response(
            HealthTicketSerializer(ticket).data,
            status=status.HTTP_201_CREATED
        )
    
    @extend_schema(
        tags=['Health Tickets'],
        description='Get my health tickets'
    )
    @action(detail=False, methods=['get'])
    def my_tickets(self, request):
        """Get current user's tickets."""
        tickets = HealthTicket.objects.for_patient(request.user)
        serializer = self.get_serializer(tickets, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Health Tickets'],
        description='Get upcoming appointments'
    )
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming appointments."""
        days = int(request.query_params.get('days', 7))
        tickets = HealthTicket.objects.upcoming(patient=request.user, days=days)
        serializer = self.get_serializer(tickets, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Health Tickets'],
        request=UpdateHealthTicketStatusSerializer,
        description='Update ticket status (check-in, start consultation, etc.)'
    )
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update ticket status."""
        ticket = self.get_object()
        serializer = UpdateHealthTicketStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        action_name = serializer.validated_data['action']
        
        try:
            if action_name == 'check_in':
                ticket.check_in()
                message = 'Patient checked in successfully'
            
            elif action_name == 'start_consultation':
                ticket.start_consultation()
                message = 'Consultation started'
            
            elif action_name == 'complete_consultation':
                ticket.complete_consultation()
                message = 'Consultation completed'
            
            elif action_name == 'complete':
                ticket.complete()
                message = 'Ticket completed'
            
            elif action_name == 'cancel':
                reason = serializer.validated_data.get('cancellation_reason', '')
                ticket.cancel(reason=reason)
                message = 'Ticket cancelled'
            
            else:
                return Response(
                    {'error': 'Invalid action'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update notes if provided
            notes = serializer.validated_data.get('notes')
            if notes:
                ticket.staff_notes = notes
                ticket.save(update_fields=['staff_notes', 'updated_at'])
            
            return Response({
                'message': message,
                'ticket': HealthTicketSerializer(ticket).data
            })
        
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        tags=['Health Tickets'],
        description='Cancel a ticket'
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a health ticket."""
        ticket = self.get_object()
        
        # Only patient or provider can cancel
        if ticket.patient != request.user and not request.user.is_staff:
            if not hasattr(request.user, 'healthcare_provider') or \
               ticket.provider != request.user.healthcare_provider:
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        reason = request.data.get('reason', 'Cancelled by user')
        
        try:
            ticket.cancel(reason=reason)
            return Response({
                'message': 'Ticket cancelled successfully',
                'ticket': HealthTicketSerializer(ticket).data
            })
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


@extend_schema_view(
    list=extend_schema(tags=['Medical Records'], description='List medical records'),
    retrieve=extend_schema(tags=['Medical Records'], description='Get medical record details'),
    create=extend_schema(tags=['Medical Records'], description='Create a medical record (doctor only)'),
)
class MedicalRecordViewSet(viewsets.ModelViewSet):
    """
    ViewSet for medical records.
    Only accessible by patient and their doctors.
    """
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['patient', 'doctor', 'health_ticket']
    ordering_fields = ['consultation_date', 'created_at']
    ordering = ['-consultation_date']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateMedicalRecordSerializer
        return MedicalRecordSerializer
    
    def get_queryset(self):
        """Filter records based on user."""
        user = self.request.user
        
        if user.is_staff:
            return MedicalRecord.objects.all()
        
        # Doctors see their own records
        if user.user_type in ['healthcare_provider', 'doctor']:
            return MedicalRecord.objects.by_doctor(user)
        
        # Patients see their own records
        return MedicalRecord.objects.for_patient(user)
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create a new medical record."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create record
        record = serializer.save(
            patient=serializer.validated_data['health_ticket'].patient,
            doctor=request.user
        )
        
        return Response(
            MedicalRecordSerializer(record).data,
            status=status.HTTP_201_CREATED
        )
    
    @extend_schema(
        tags=['Medical Records'],
        description='Get my medical records'
    )
    @action(detail=False, methods=['get'])
    def my_records(self, request):
        """Get current user's medical records."""
        records = MedicalRecord.objects.for_patient(request.user)
        serializer = self.get_serializer(records, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(tags=['Prescriptions'], description='List prescriptions'),
    retrieve=extend_schema(tags=['Prescriptions'], description='Get prescription details'),
    create=extend_schema(tags=['Prescriptions'], description='Create a prescription (doctor only)'),
)
class PrescriptionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for prescriptions.
    """
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['patient', 'doctor', 'is_dispensed']
    search_fields = ['prescription_number']
    ordering_fields = ['issue_date', 'expiry_date']
    ordering = ['-issue_date']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreatePrescriptionSerializer
        elif self.action == 'dispense':
            return DispensePrescriptionSerializer
        return PrescriptionSerializer
    
    def get_queryset(self):
        """Filter prescriptions based on user."""
        user = self.request.user
        
        if user.is_staff:
            return Prescription.objects.all()
        
        # Doctors see their own prescriptions
        if user.user_type in ['healthcare_provider', 'doctor']:
            return Prescription.objects.by_doctor(user)
        
        # Patients see their own prescriptions
        return Prescription.objects.for_patient(user)
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create a new prescription with medications."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        health_ticket = HealthTicket.objects.get(id=serializer.validated_data['health_ticket_id'])
        medical_record = MedicalRecord.objects.get(id=serializer.validated_data['medical_record_id'])
        
        # Calculate expiry date
        expiry_days = serializer.validated_data.get('expiry_days', 30)
        expiry_date = timezone.now().date() + timedelta(days=expiry_days)
        
        # Create prescription
        prescription = Prescription.objects.create(
            health_ticket=health_ticket,
            medical_record=medical_record,
            patient=health_ticket.patient,
            doctor=request.user,
            expiry_date=expiry_date,
            notes=serializer.validated_data.get('notes', '')
        )
        
        # Add medications
        for med_data in serializer.validated_data['medications']:
            PrescriptionMedication.objects.create(
                prescription=prescription,
                **med_data
            )
        
        # Update ticket status
        if health_ticket.status == HealthTicket.CONSULTATION_COMPLETED:
            health_ticket.status = HealthTicket.PRESCRIPTION_ISSUED
            health_ticket.save(update_fields=['status', 'updated_at'])
        
        return Response(
            PrescriptionSerializer(prescription).data,
            status=status.HTTP_201_CREATED
        )
    
    @extend_schema(
        tags=['Prescriptions'],
        description='Get my prescriptions'
    )
    @action(detail=False, methods=['get'])
    def my_prescriptions(self, request):
        """Get current user's prescriptions."""
        prescriptions = Prescription.objects.for_patient(request.user)
        serializer = self.get_serializer(prescriptions, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Prescriptions'],
        description='Get active (non-expired) prescriptions'
    )
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active prescriptions."""
        prescriptions = Prescription.objects.active(patient=request.user)
        serializer = self.get_serializer(prescriptions, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Prescriptions'],
        request=DispensePrescriptionSerializer,
        description='Dispense a prescription (pharmacy only)'
    )
    @action(detail=True, methods=['post'])
    def dispense(self, request, pk=None):
        """Mark prescription as dispensed."""
        prescription = self.get_object()
        
        if prescription.is_dispensed:
            return Response(
                {'error': 'Prescription already dispensed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if expired
        if prescription.expiry_date < timezone.now().date():
            return Response(
                {'error': 'Prescription expired'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = DispensePrescriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        prescription.is_dispensed = True
        prescription.dispensed_at = timezone.now()
        prescription.dispensed_by_name = serializer.validated_data['pharmacy_name']
        prescription.notes += f"\n\nDispensed: {serializer.validated_data.get('notes', '')}"
        prescription.save()
        
        return Response({
            'message': 'Prescription dispensed successfully',
            'prescription': PrescriptionSerializer(prescription).data
        })
