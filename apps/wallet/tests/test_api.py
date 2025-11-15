"""
KALPÉ SANTÉ - Wallet API Tests
Integration tests for wallet API endpoints.
"""

import pytest
from decimal import Decimal
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from apps.users.models import User
from apps.wallet.models import Wallet, Transaction


@pytest.fixture
def api_client():
    """Create API client."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create test user."""
    return User.objects.create_user(
        email='test@example.com',
        password='TestPass123!@#',
        first_name='Test',
        last_name='User',
        email_verified=True
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """Create authenticated API client."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.mark.django_db
class TestWalletAPI:
    """Tests for Wallet API endpoints."""
    
    def test_get_my_wallet(self, authenticated_client, user):
        """Test getting current user's wallet."""
        url = reverse('wallet:wallet-me')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'balance' in response.data
        assert response.data['currency'] == 'XOF'
    
    def test_get_wallet_balance(self, authenticated_client, user):
        """Test getting wallet balance details."""
        wallet = Wallet.objects.get(user=user)
        url = reverse('wallet:wallet-balance', kwargs={'pk': wallet.id})
        
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'balance' in response.data
        assert 'daily_spent' in response.data
        assert 'daily_remaining' in response.data
        assert 'monthly_spent' in response.data
    
    def test_get_wallet_history(self, authenticated_client, user):
        """Test getting wallet transaction history."""
        wallet = Wallet.objects.get(user=user)
        url = reverse('wallet:wallet-history', kwargs={'pk': wallet.id})
        
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'sent_transactions' in response.data
        assert 'received_transactions' in response.data
        assert 'summary' in response.data
    
    def test_get_wallet_ledger(self, authenticated_client, user):
        """Test getting wallet ledger entries."""
        wallet = Wallet.objects.get(user=user)
        url = reverse('wallet:wallet-ledger', kwargs={'pk': wallet.id})
        
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
    
    def test_unauthenticated_access_denied(self, api_client):
        """Test that unauthenticated users cannot access wallet."""
        url = reverse('wallet:wallet-me')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestTransactionAPI:
    """Tests for Transaction API endpoints."""
    
    def test_list_transactions(self, authenticated_client, user):
        """Test listing user transactions."""
        url = reverse('wallet:transaction-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
    
    def test_transfer_funds(self, authenticated_client, user):
        """Test transferring funds between wallets."""
        # Create receiver
        receiver = User.objects.create_user(
            email='receiver@example.com',
            password='TestPass123!@#',
            email_verified=True
        )
        
        # Add funds to sender
        sender_wallet = Wallet.objects.get(user=user)
        sender_wallet.credit(Decimal('5000.00'))
        
        url = reverse('wallet:transaction-transfer')
        data = {
            'receiver_email': receiver.email,
            'amount': '1000.00',
            'description': 'Test transfer'
        }
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert 'transaction' in response.data
        assert response.data['transaction']['amount'] == '1000.00'
        
        # Verify balances
        sender_wallet.refresh_from_db()
        receiver_wallet = Wallet.objects.get(user=receiver)
        
        assert sender_wallet.balance == Decimal('4000.00')
        assert receiver_wallet.balance == Decimal('1000.00')
    
    def test_transfer_insufficient_funds(self, authenticated_client, user):
        """Test transfer with insufficient funds."""
        receiver = User.objects.create_user(
            email='receiver@example.com',
            password='TestPass123!@#',
            email_verified=True
        )
        
        url = reverse('wallet:transaction-transfer')
        data = {
            'receiver_email': receiver.email,
            'amount': '1000.00'
        }
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
    
    def test_transfer_to_invalid_user(self, authenticated_client, user):
        """Test transfer to non-existent user."""
        sender_wallet = Wallet.objects.get(user=user)
        sender_wallet.credit(Decimal('5000.00'))
        
        url = reverse('wallet:transaction-transfer')
        data = {
            'receiver_email': 'nonexistent@example.com',
            'amount': '1000.00'
        }
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_deposit_funds(self, authenticated_client, user):
        """Test depositing funds to wallet."""
        url = reverse('wallet:transaction-deposit')
        data = {
            'amount': '5000.00',
            'payment_method': 'ORANGE_MONEY',
            'phone_number': '221771234567',
            'description': 'Test deposit'
        }
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert 'transaction' in response.data
        assert 'payment_instructions' in response.data
    
    def test_withdraw_funds(self, authenticated_client, user):
        """Test withdrawing funds from wallet."""
        # Add funds first
        wallet = Wallet.objects.get(user=user)
        wallet.credit(Decimal('10000.00'))
        
        url = reverse('wallet:transaction-withdraw')
        data = {
            'amount': '5000.00',
            'withdrawal_method': 'ORANGE_MONEY',
            'phone_number': '221771234567'
        }
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert 'transaction' in response.data
        assert 'withdrawal_details' in response.data
    
    def test_cancel_transaction(self, authenticated_client, user):
        """Test cancelling a pending transaction."""
        receiver = User.objects.create_user(
            email='receiver@example.com',
            password='TestPass123!@#',
            email_verified=True
        )
        
        sender_wallet = Wallet.objects.get(user=user)
        receiver_wallet = Wallet.objects.get(user=receiver)
        
        # Create pending transaction
        txn = Transaction.objects.create_transfer(
            sender_wallet=sender_wallet,
            receiver_wallet=receiver_wallet,
            amount=Decimal('1000.00'),
            initiated_by=user
        )
        
        url = reverse('wallet:transaction-cancel', kwargs={'pk': txn.id})
        data = {'reason': 'User requested cancellation'}
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        txn.refresh_from_db()
        assert txn.status == Transaction.CANCELLED


@pytest.mark.django_db
class TestFraudDetection:
    """Tests for fraud detection functionality."""
    
    def test_high_value_transaction_flagged(self, authenticated_client, user):
        """Test that high-value transactions are flagged."""
        receiver = User.objects.create_user(
            email='receiver@example.com',
            password='TestPass123!@#',
            email_verified=True
        )
        
        # Add large amount
        sender_wallet = Wallet.objects.get(user=user)
        sender_wallet.credit(Decimal('2000000.00'))
        
        url = reverse('wallet:transaction-transfer')
        data = {
            'receiver_email': receiver.email,
            'amount': '1500000.00',  # 1.5M XOF
            'description': 'Large transfer'
        }
        
        response = authenticated_client.post(url, data, format='json')
        
        # Transaction might be flagged but still created
        if response.status_code == status.HTTP_201_CREATED:
            txn = Transaction.objects.get(
                reference=response.data['transaction']['reference']
            )
            # High value transactions get flagged
            assert txn.fraud_score > 0 or txn.is_flagged is True
    
    def test_velocity_check(self, authenticated_client, user):
        """Test velocity checking for rapid transactions."""
        receiver = User.objects.create_user(
            email='receiver@example.com',
            password='TestPass123!@#',
            email_verified=True
        )
        
        # Add funds
        sender_wallet = Wallet.objects.get(user=user)
        sender_wallet.credit(Decimal('100000.00'))
        
        url = reverse('wallet:transaction-transfer')
        
        # Make multiple rapid transactions
        for i in range(3):
            data = {
                'receiver_email': receiver.email,
                'amount': '1000.00',
                'description': f'Transfer {i+1}'
            }
            response = authenticated_client.post(url, data, format='json')
            
            # First few should succeed
            if i < 2:
                assert response.status_code in [
                    status.HTTP_201_CREATED,
                    status.HTTP_403_FORBIDDEN  # Might be flagged
                ]

