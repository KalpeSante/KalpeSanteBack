"""
KALPÉ SANTÉ - Healthcare URLs
URL patterns for healthcare API endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    HealthcareProviderViewSet,
    HealthTicketViewSet,
    MedicalRecordViewSet,
    PrescriptionViewSet,
)

app_name = 'healthcare'

router = DefaultRouter()
router.register(r'providers', HealthcareProviderViewSet, basename='provider')
router.register(r'tickets', HealthTicketViewSet, basename='ticket')
router.register(r'medical-records', MedicalRecordViewSet, basename='medical-record')
router.register(r'prescriptions', PrescriptionViewSet, basename='prescription')

urlpatterns = [
    path('', include(router.urls)),
]

