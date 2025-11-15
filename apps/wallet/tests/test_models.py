"""
KALPÉ SANTÉ - Wallet Model Tests
Unit tests for wallet models.
"""

import pytest
from decimal import Decimal
from django.utils import timezone
from apps.wallet.models import Wallet, Transaction, FraudRule, WalletLedger
from apps.users.models import User
from apps.core.exceptions import (
    InsufficientFundsException,
    TransactionException,
)


@pytest.mark.django_db
class TestWalletModel:
    """Tests for Wallet model."""
    
    def test_create_wallet(self):
        """Test wallet creation."""
        user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!@#',
            first_name='Test',
            last_name='User'
        )
        
        wallet = Wallet.objects.get(user=user)  # Auto-created by signal
        
        assert wallet.balance == Decimal('0.00')
        assert wallet.currency == 'XOF'
        assert wallet.is_active is True
        assert wallet.is_locked is False
    
    def test_wallet_credit(self):
        """Test crediting wallet."""
        user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!@#'
        )
        wallet = Wallet.objects.get(user=user)
        
        initial_balance = wallet.balance
        amount = Decimal('1000.00')
        
        new_balance = wallet.credit(amount)
        
        assert new_balance == initial_balance + amount
        assert wallet.balance == initial_balance + amount
    
    def test_wallet_debit(self):
        """Test debiting wallet."""
        user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!@#'
        )
        wallet = Wallet.objects.get(user=user)
        
        # Add funds first
        wallet.credit(Decimal('1000.00'))
        
        initial_balance = wallet.balance
        amount = Decimal('500.00')
        
        new_balance = wallet.debit(amount)
        
        assert new_balance == initial_balance - amount
        assert wallet.balance == initial_balance - amount
    
    def test_wallet_debit_insufficient_funds(self):
        """Test debit with insufficient funds raises exception."""
        user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!@#'
        )
        wallet = Wallet.objects.get(user=user)
        
        with pytest.raises(InsufficientFundsException):
            wallet.debit(Decimal('1000.00'))
    
    def test_wallet_lock_unlock(self):
        """Test locking and unlocking wallet."""
        user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!@#'
        )
        wallet = Wallet.objects.get(user=user)
        
        # Lock wallet
        wallet.lock(reason='Suspicious activity', locked_by=user)
        
        assert wallet.is_locked is True
        assert wallet.locked_reason == 'Suspicious activity'
        assert wallet.locked_by == user
        assert wallet.locked_at is not None
        
        # Unlock wallet
        wallet.unlock()
        
        assert wallet.is_locked is False
        assert wallet.locked_reason == ''
        assert wallet.locked_by is None
    
    def test_wallet_cannot_debit_when_locked(self):
        """Test that locked wallet cannot be debited."""
        user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!@#'
        )
        wallet = Wallet.objects.get(user=user)
        wallet.credit(Decimal('1000.00'))
        
        wallet.lock(reason='Test lock')
        
        with pytest.raises(TransactionException):
            wallet.debit(Decimal('100.00'))
    
    def test_get_daily_spent(self):
        """Test getting daily spent amount."""
        user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!@#'
        )
        wallet = Wallet.objects.get(user=user)
        
        assert wallet.get_daily_spent() == Decimal('0.00')
    
    def test_can_send(self):
        """Test can_send method."""
        user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!@#'
        )
        wallet = Wallet.objects.get(user=user)
        
        # No balance
        assert wallet.can_send(Decimal('100.00')) is False
        
        # Add balance
        wallet.credit(Decimal('1000.00'))
        assert wallet.can_send(Decimal('100.00')) is True
        
        # Lock wallet
        wallet.lock(reason='Test')
        assert wallet.can_send(Decimal('100.00')) is False


@pytest.mark.django_db
class TestTransactionModel:
    """Tests for Transaction model."""
    
    def test_create_transfer_transaction(self):
        """Test creating a transfer transaction."""
        sender = User.objects.create_user(
            email='sender@example.com',
            password='TestPass123!@#'
        )
        receiver = User.objects.create_user(
            email='receiver@example.com',
            password='TestPass123!@#'
        )
        
        sender_wallet = Wallet.objects.get(user=sender)
        receiver_wallet = Wallet.objects.get(user=receiver)
        
        txn = Transaction.objects.create_transfer(
            sender_wallet=sender_wallet,
            receiver_wallet=receiver_wallet,
            amount=Decimal('1000.00'),
            description='Test transfer',
            initiated_by=sender
        )
        
        assert txn.transaction_type == Transaction.TRANSFER
        assert txn.status == Transaction.PENDING
        assert txn.amount == Decimal('1000.00')
        assert txn.reference is not None
    
    def test_execute_transfer_transaction(self):
        """Test executing a transfer transaction."""
        sender = User.objects.create_user(
            email='sender@example.com',
            password='TestPass123!@#'
        )
        receiver = User.objects.create_user(
            email='receiver@example.com',
            password='TestPass123!@#'
        )
        
        sender_wallet = Wallet.objects.get(user=sender)
        receiver_wallet = Wallet.objects.get(user=receiver)
        
        # Add funds to sender
        sender_wallet.credit(Decimal('5000.00'))
        
        txn = Transaction.objects.create_transfer(
            sender_wallet=sender_wallet,
            receiver_wallet=receiver_wallet,
            amount=Decimal('1000.00'),
            initiated_by=sender
        )
        
        initial_sender_balance = sender_wallet.balance
        initial_receiver_balance = receiver_wallet.balance
        
        txn.execute()
        
        sender_wallet.refresh_from_db()
        receiver_wallet.refresh_from_db()
        
        assert txn.status == Transaction.COMPLETED
        assert sender_wallet.balance == initial_sender_balance - Decimal('1000.00')
        assert receiver_wallet.balance == initial_receiver_balance + Decimal('1000.00')
    
    def test_transaction_reference_is_generated(self):
        """Test that transaction reference is auto-generated."""
        sender = User.objects.create_user(
            email='sender@example.com',
            password='TestPass123!@#'
        )
        wallet = Wallet.objects.get(user=sender)
        
        txn = Transaction.objects.create_deposit(
            receiver_wallet=wallet,
            amount=Decimal('1000.00')
        )
        
        assert txn.reference is not None
        assert txn.reference.startswith('TXN')
    
    def test_cancel_transaction(self):
        """Test cancelling a transaction."""
        sender = User.objects.create_user(
            email='sender@example.com',
            password='TestPass123!@#'
        )
        receiver = User.objects.create_user(
            email='receiver@example.com',
            password='TestPass123!@#'
        )
        
        sender_wallet = Wallet.objects.get(user=sender)
        receiver_wallet = Wallet.objects.get(user=receiver)
        
        txn = Transaction.objects.create_transfer(
            sender_wallet=sender_wallet,
            receiver_wallet=receiver_wallet,
            amount=Decimal('1000.00'),
            initiated_by=sender
        )
        
        txn.cancel(reason='User cancelled')
        
        assert txn.status == Transaction.CANCELLED
        assert txn.failure_reason == 'User cancelled'
    
    def test_flag_transaction(self):
        """Test flagging transaction for review."""
        sender = User.objects.create_user(
            email='sender@example.com',
            password='TestPass123!@#'
        )
        wallet = Wallet.objects.get(user=sender)
        
        txn = Transaction.objects.create_deposit(
            receiver_wallet=wallet,
            amount=Decimal('1000.00')
        )
        
        txn.flag_for_review(reason='Suspicious activity')
        
        assert txn.is_flagged is True
        assert txn.flagged_reason == 'Suspicious activity'


@pytest.mark.django_db
class TestFraudRuleModel:
    """Tests for FraudRule model."""
    
    def test_create_fraud_rule(self):
        """Test creating a fraud rule."""
        rule = FraudRule.objects.create(
            name='High Amount Threshold',
            description='Flag transactions over 1M XOF',
            rule_type='AMOUNT_THRESHOLD',
            threshold_value=Decimal('1000000.00'),
            fraud_score=50,
            auto_block=False
        )
        
        assert rule.name == 'High Amount Threshold'
        assert rule.rule_type == 'AMOUNT_THRESHOLD'
        assert rule.is_active is True
    
    def test_fraud_rule_managers(self):
        """Test fraud rule custom managers."""
        FraudRule.objects.create(
            name='Amount Rule',
            description='Test',
            rule_type='AMOUNT_THRESHOLD',
            threshold_value=Decimal('100000.00'),
            fraud_score=10
        )
        
        FraudRule.objects.create(
            name='Velocity Rule',
            description='Test',
            rule_type='VELOCITY',
            time_window_minutes=60,
            max_occurrences=5,
            fraud_score=20
        )
        
        assert FraudRule.objects.active_rules().count() == 2
        assert FraudRule.objects.amount_threshold_rules().count() == 1
        assert FraudRule.objects.velocity_rules().count() == 1

