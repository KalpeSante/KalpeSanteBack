"""
KALPÉ SANTÉ - Wallet Managers
Custom managers for wallet operations.
"""

from decimal import Decimal
from django.db import models, transaction
from django.utils import timezone
from django.db.models import Sum, Count, Q, F
from datetime import timedelta


class WalletManager(models.Manager):
    """Manager for Wallet model."""
    
    def create_wallet_for_user(self, user, initial_balance=Decimal('0.00')):
        """Create a new wallet for a user."""
        from .models import Wallet
        
        wallet = self.create(
            user=user,
            balance=initial_balance,
            currency='XOF'
        )
        return wallet
    
    def get_or_create_for_user(self, user):
        """Get or create wallet for user."""
        return self.get_or_create(
            user=user,
            defaults={
                'balance': Decimal('0.00'),
                'currency': 'XOF'
            }
        )
    
    def active_wallets(self):
        """Get all active wallets."""
        return self.filter(is_active=True, is_locked=False, deleted_at__isnull=True)
    
    def locked_wallets(self):
        """Get all locked wallets."""
        return self.filter(is_locked=True, deleted_at__isnull=True)
    
    def with_balance_above(self, amount):
        """Get wallets with balance above specified amount."""
        return self.filter(balance__gte=amount, deleted_at__isnull=True)


class TransactionManager(models.Manager):
    """Manager for Transaction model."""
    
    @transaction.atomic
    def create_transfer(self, sender_wallet, receiver_wallet, amount, description='', initiated_by=None, metadata=None):
        """Create a new transfer transaction."""
        from .models import Transaction
        
        txn = self.create(
            transaction_type=Transaction.TRANSFER,
            sender_wallet=sender_wallet,
            receiver_wallet=receiver_wallet,
            amount=amount,
            currency='XOF',
            description=description,
            initiated_by=initiated_by,
            metadata=metadata or {}
        )
        return txn
    
    @transaction.atomic
    def create_deposit(self, receiver_wallet, amount, description='', external_reference='', initiated_by=None, metadata=None):
        """Create a new deposit transaction."""
        from .models import Transaction
        
        txn = self.create(
            transaction_type=Transaction.DEPOSIT,
            receiver_wallet=receiver_wallet,
            amount=amount,
            currency='XOF',
            description=description,
            external_reference=external_reference,
            initiated_by=initiated_by,
            metadata=metadata or {}
        )
        return txn
    
    @transaction.atomic
    def create_withdrawal(self, sender_wallet, amount, fee=Decimal('0.00'), description='', external_reference='', initiated_by=None, metadata=None):
        """Create a new withdrawal transaction."""
        from .models import Transaction
        
        txn = self.create(
            transaction_type=Transaction.WITHDRAWAL,
            sender_wallet=sender_wallet,
            amount=amount,
            currency='XOF',
            fee=fee,
            description=description,
            external_reference=external_reference,
            initiated_by=initiated_by,
            metadata=metadata or {}
        )
        return txn
    
    @transaction.atomic
    def create_payment(self, sender_wallet, receiver_wallet, amount, fee=Decimal('0.00'), description='', initiated_by=None, metadata=None):
        """Create a new payment transaction."""
        from .models import Transaction
        
        txn = self.create(
            transaction_type=Transaction.PAYMENT,
            sender_wallet=sender_wallet,
            receiver_wallet=receiver_wallet,
            amount=amount,
            currency='XOF',
            fee=fee,
            description=description,
            initiated_by=initiated_by,
            metadata=metadata or {}
        )
        return txn
    
    @transaction.atomic
    def create_sponsorship(self, sponsor_wallet, beneficiary_wallet, amount, description='', initiated_by=None, metadata=None):
        """Create a new sponsorship transaction."""
        from .models import Transaction
        
        txn = self.create(
            transaction_type=Transaction.SPONSORSHIP,
            sender_wallet=sponsor_wallet,
            receiver_wallet=beneficiary_wallet,
            amount=amount,
            currency='XOF',
            description=description,
            initiated_by=initiated_by,
            metadata=metadata or {}
        )
        return txn
    
    def pending(self):
        """Get all pending transactions."""
        from .models import Transaction
        return self.filter(status=Transaction.PENDING, deleted_at__isnull=True)
    
    def completed(self):
        """Get all completed transactions."""
        from .models import Transaction
        return self.filter(status=Transaction.COMPLETED, deleted_at__isnull=True)
    
    def failed(self):
        """Get all failed transactions."""
        from .models import Transaction
        return self.filter(status=Transaction.FAILED, deleted_at__isnull=True)
    
    def flagged(self):
        """Get all flagged transactions."""
        return self.filter(is_flagged=True, deleted_at__isnull=True)
    
    def unreconciled(self):
        """Get all unreconciled completed transactions."""
        from .models import Transaction
        return self.filter(
            status=Transaction.COMPLETED,
            is_reconciled=False,
            deleted_at__isnull=True
        )
    
    def for_wallet(self, wallet):
        """Get all transactions for a wallet (sent or received)."""
        return self.filter(
            Q(sender_wallet=wallet) | Q(receiver_wallet=wallet),
            deleted_at__isnull=True
        )
    
    def recent(self, days=30):
        """Get recent transactions."""
        since = timezone.now() - timedelta(days=days)
        return self.filter(created_at__gte=since, deleted_at__isnull=True)
    
    def high_value(self, threshold=100000):
        """Get high-value transactions."""
        return self.filter(amount__gte=threshold, deleted_at__isnull=True)
    
    def get_daily_stats(self, date=None):
        """Get transaction statistics for a specific date."""
        from .models import Transaction
        
        if date is None:
            date = timezone.now().date()
        
        transactions = self.filter(
            created_at__date=date,
            deleted_at__isnull=True
        )
        
        return {
            'total_count': transactions.count(),
            'completed_count': transactions.filter(status=Transaction.COMPLETED).count(),
            'failed_count': transactions.filter(status=Transaction.FAILED).count(),
            'total_volume': transactions.filter(status=Transaction.COMPLETED).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00'),
            'total_fees': transactions.filter(status=Transaction.COMPLETED).aggregate(
                total=Sum('fee')
            )['total'] or Decimal('0.00'),
            'flagged_count': transactions.filter(is_flagged=True).count(),
        }


class FraudRuleManager(models.Manager):
    """Manager for FraudRule model."""
    
    def active_rules(self):
        """Get all active fraud rules."""
        return self.filter(is_active=True, deleted_at__isnull=True)
    
    def amount_threshold_rules(self):
        """Get amount threshold rules."""
        return self.active_rules().filter(rule_type='AMOUNT_THRESHOLD')
    
    def velocity_rules(self):
        """Get velocity check rules."""
        return self.active_rules().filter(rule_type='VELOCITY')
    
    def pattern_rules(self):
        """Get pattern detection rules."""
        return self.active_rules().filter(rule_type='PATTERN')

