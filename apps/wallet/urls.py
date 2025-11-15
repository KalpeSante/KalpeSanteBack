"""
KALPÉ SANTÉ - Wallet URLs
URL patterns for wallet API endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WalletViewSet, TransactionViewSet, FraudRuleViewSet

app_name = 'wallet'

router = DefaultRouter()
router.register(r'wallets', WalletViewSet, basename='wallet')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'fraud-rules', FraudRuleViewSet, basename='fraud-rule')

urlpatterns = [
    path('', include(router.urls)),
]


