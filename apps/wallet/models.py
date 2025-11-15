"""
KALPÉ SANTÉ - Wallet Models
Secure wallet system with ACID transactions, fraud detection, and reconciliation.
"""

from decimal import Decimal
from django.db import models, transaction
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from apps.core.models import BaseModel, TimestampedModel, UUIDModel
from apps.core.exceptions import InsufficientFundsException, TransactionException
from .managers import WalletManager, TransactionManager, FraudRuleManager


class Wallet(BaseModel):
    """
    User wallet for managing funds.
    Supports ACID transactions and balance integrity.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,  # Never delete wallet if user exists
        related_name='wallet'
    )
    balance = models.DecimalField(
        _('balance'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    currency = models.CharField(
        _('currency'),
        max_length=3,
        default='XOF'
    )
    is_active = models.BooleanField(
        _('is active'),
        default=True,
        help_text=_('Inactive wallets cannot send or receive funds')
    )
    is_locked = models.BooleanField(
        _('is locked'),
        default=False,
        help_text=_('Locked wallets are frozen due to security concerns')
    )
    locked_reason = models.TextField(
        _('locked reason'),
        blank=True,
        help_text=_('Reason for wallet lock')
    )
    locked_at = models.DateTimeField(
        _('locked at'),
        null=True,
        blank=True
    )
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='locked_wallets'
    )
    daily_limit = models.DecimalField(
        _('daily transaction limit'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('500000.00'),  # 500,000 XOF
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    monthly_limit = models.DecimalField(
        _('monthly transaction limit'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('5000000.00'),  # 5,000,000 XOF
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    objects = WalletManager()
    
    class Meta:
        db_table = 'wallets'
        verbose_name = _('Wallet')
        verbose_name_plural = _('Wallets')
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['is_active', 'is_locked']),
        ]
    
    def __str__(self):
        return f"Wallet {self.user.email} - {self.balance} {self.currency}"
    
    @transaction.atomic
    def credit(self, amount, transaction_ref=None, description=''):
        """
        Credit wallet with amount.
        This method is atomic and thread-safe.
        """
        if amount <= 0:
            raise TransactionException("Amount must be positive")
        
        if not self.is_active:
            raise TransactionException("Wallet is not active")
        
        if self.is_locked:
            raise TransactionException("Wallet is locked")
        
        # Use select_for_update to prevent race conditions
        wallet = Wallet.objects.select_for_update().get(pk=self.pk)
        wallet.balance += Decimal(str(amount))
        wallet.save(update_fields=['balance', 'updated_at'])
        
        # Refresh from database to ensure we have the latest balance
        self.refresh_from_db()
        
        return self.balance
    
    @transaction.atomic
    def debit(self, amount, transaction_ref=None, description=''):
        """
        Debit wallet with amount.
        This method is atomic and thread-safe.
        """
        if amount <= 0:
            raise TransactionException("Amount must be positive")
        
        if not self.is_active:
            raise TransactionException("Wallet is not active")
        
        if self.is_locked:
            raise TransactionException("Wallet is locked")
        
        # Use select_for_update to prevent race conditions
        wallet = Wallet.objects.select_for_update().get(pk=self.pk)
        
        if wallet.balance < Decimal(str(amount)):
            raise InsufficientFundsException(
                f"Insufficient funds. Balance: {wallet.balance}, Required: {amount}"
            )
        
        wallet.balance -= Decimal(str(amount))
        wallet.save(update_fields=['balance', 'updated_at'])
        
        # Refresh from database to ensure we have the latest balance
        self.refresh_from_db()
        
        return self.balance
    
    def lock(self, reason, locked_by=None):
        """Lock wallet for security reasons."""
        self.is_locked = True
        self.locked_reason = reason
        self.locked_at = timezone.now()
        self.locked_by = locked_by
        self.save(update_fields=['is_locked', 'locked_reason', 'locked_at', 'locked_by', 'updated_at'])
    
    def unlock(self):
        """Unlock wallet."""
        self.is_locked = False
        self.locked_reason = ''
        self.locked_at = None
        self.locked_by = None
        self.save(update_fields=['is_locked', 'locked_reason', 'locked_at', 'locked_by', 'updated_at'])
    
    def get_daily_spent(self):
        """Get total amount spent today."""
        today = timezone.now().date()
        return Transaction.objects.filter(
            sender_wallet=self,
            status='COMPLETED',
            created_at__date=today
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
    
    def get_monthly_spent(self):
        """Get total amount spent this month."""
        now = timezone.now()
        return Transaction.objects.filter(
            sender_wallet=self,
            status='COMPLETED',
            created_at__year=now.year,
            created_at__month=now.month
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
    
    def can_send(self, amount):
        """Check if wallet can send specified amount."""
        if not self.is_active or self.is_locked:
            return False
        
        if self.balance < amount:
            return False
        
        daily_spent = self.get_daily_spent()
        if daily_spent + amount > self.daily_limit:
            return False
        
        monthly_spent = self.get_monthly_spent()
        if monthly_spent + amount > self.monthly_limit:
            return False
        
        return True


class Transaction(BaseModel):
    """
    Financial transaction with ACID guarantees.
    All transactions are immutable once completed.
    """
    
    # Transaction Types
    DEPOSIT = 'DEPOSIT'
    WITHDRAWAL = 'WITHDRAWAL'
    TRANSFER = 'TRANSFER'
    PAYMENT = 'PAYMENT'
    REFUND = 'REFUND'
    SPONSORSHIP = 'SPONSORSHIP'
    HEALTHCARE_PAYMENT = 'HEALTHCARE_PAYMENT'
    PHARMACY_PAYMENT = 'PHARMACY_PAYMENT'
    
    TRANSACTION_TYPES = [
        (DEPOSIT, _('Deposit')),
        (WITHDRAWAL, _('Withdrawal')),
        (TRANSFER, _('Transfer')),
        (PAYMENT, _('Payment')),
        (REFUND, _('Refund')),
        (SPONSORSHIP, _('Sponsorship')),
        (HEALTHCARE_PAYMENT, _('Healthcare Payment')),
        (PHARMACY_PAYMENT, _('Pharmacy Payment')),
    ]
    
    # Transaction Status
    PENDING = 'PENDING'
    PROCESSING = 'PROCESSING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    CANCELLED = 'CANCELLED'
    REVERSED = 'REVERSED'
    
    STATUS_CHOICES = [
        (PENDING, _('Pending')),
        (PROCESSING, _('Processing')),
        (COMPLETED, _('Completed')),
        (FAILED, _('Failed')),
        (CANCELLED, _('Cancelled')),
        (REVERSED, _('Reversed')),
    ]
    
    transaction_type = models.CharField(
        _('transaction type'),
        max_length=20,
        choices=TRANSACTION_TYPES
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
        db_index=True
    )
    sender_wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name='sent_transactions',
        null=True,
        blank=True
    )
    receiver_wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name='received_transactions',
        null=True,
        blank=True
    )
    amount = models.DecimalField(
        _('amount'),
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(
        _('currency'),
        max_length=3,
        default='XOF'
    )
    fee = models.DecimalField(
        _('transaction fee'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    description = models.TextField(
        _('description'),
        blank=True
    )
    reference = models.CharField(
        _('reference'),
        max_length=100,
        unique=True,
        db_index=True,
        help_text=_('Unique transaction reference')
    )
    external_reference = models.CharField(
        _('external reference'),
        max_length=255,
        blank=True,
        help_text=_('Reference from external payment provider')
    )
    metadata = models.JSONField(
        _('metadata'),
        default=dict,
        blank=True,
        help_text=_('Additional transaction data')
    )
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='initiated_transactions'
    )
    
    # Reconciliation fields
    is_reconciled = models.BooleanField(
        _('is reconciled'),
        default=False,
        db_index=True
    )
    reconciled_at = models.DateTimeField(
        _('reconciled at'),
        null=True,
        blank=True
    )
    reconciled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reconciled_transactions'
    )
    
    # Fraud detection fields
    fraud_score = models.IntegerField(
        _('fraud score'),
        default=0,
        help_text=_('0-100, higher means more suspicious')
    )
    is_flagged = models.BooleanField(
        _('is flagged for review'),
        default=False,
        db_index=True
    )
    flagged_reason = models.TextField(
        _('flagged reason'),
        blank=True
    )
    reviewed_at = models.DateTimeField(
        _('reviewed at'),
        null=True,
        blank=True
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_transactions'
    )
    
    # Timestamps
    completed_at = models.DateTimeField(
        _('completed at'),
        null=True,
        blank=True
    )
    failed_at = models.DateTimeField(
        _('failed at'),
        null=True,
        blank=True
    )
    failure_reason = models.TextField(
        _('failure reason'),
        blank=True
    )
    
    objects = TransactionManager()
    
    class Meta:
        db_table = 'transactions'
        verbose_name = _('Transaction')
        verbose_name_plural = _('Transactions')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['sender_wallet', 'status']),
            models.Index(fields=['receiver_wallet', 'status']),
            models.Index(fields=['is_flagged', 'status']),
            models.Index(fields=['is_reconciled']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.transaction_type} - {self.amount} {self.currency} - {self.status}"
    
    def save(self, *args, **kwargs):
        """Override save to ensure reference is generated."""
        if not self.reference:
            self.reference = self.generate_reference()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_reference():
        """Generate unique transaction reference."""
        import uuid
        from django.utils.crypto import get_random_string
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        random_str = get_random_string(8, allowed_chars='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        return f"TXN{timestamp}{random_str}"
    
    @transaction.atomic
    def execute(self):
        """
        Execute the transaction with ACID guarantees.
        This is the main method for processing transactions.
        """
        if self.status != self.PENDING:
            raise TransactionException(f"Transaction {self.reference} is not pending")
        
        try:
            # Update status to processing
            self.status = self.PROCESSING
            self.save(update_fields=['status', 'updated_at'])
            
            # Execute based on transaction type
            if self.transaction_type == self.TRANSFER:
                self._execute_transfer()
            elif self.transaction_type == self.DEPOSIT:
                self._execute_deposit()
            elif self.transaction_type == self.WITHDRAWAL:
                self._execute_withdrawal()
            elif self.transaction_type in [self.PAYMENT, self.HEALTHCARE_PAYMENT, self.PHARMACY_PAYMENT]:
                self._execute_payment()
            elif self.transaction_type == self.SPONSORSHIP:
                self._execute_sponsorship()
            elif self.transaction_type == self.REFUND:
                self._execute_refund()
            else:
                raise TransactionException(f"Unknown transaction type: {self.transaction_type}")
            
            # Mark as completed
            self.status = self.COMPLETED
            self.completed_at = timezone.now()
            self.save(update_fields=['status', 'completed_at', 'updated_at'])
            
        except Exception as e:
            # Mark as failed
            self.status = self.FAILED
            self.failed_at = timezone.now()
            self.failure_reason = str(e)
            self.save(update_fields=['status', 'failed_at', 'failure_reason', 'updated_at'])
            raise
    
    def _execute_transfer(self):
        """Execute wallet-to-wallet transfer."""
        if not self.sender_wallet or not self.receiver_wallet:
            raise TransactionException("Both sender and receiver wallets required for transfer")
        
        if self.sender_wallet == self.receiver_wallet:
            raise TransactionException("Cannot transfer to same wallet")
        
        # Check limits
        if not self.sender_wallet.can_send(self.amount):
            raise TransactionException("Transaction exceeds wallet limits")
        
        # Debit sender
        self.sender_wallet.debit(self.amount, self.reference, self.description)
        
        # Credit receiver
        self.receiver_wallet.credit(self.amount, self.reference, self.description)
    
    def _execute_deposit(self):
        """Execute deposit to wallet."""
        if not self.receiver_wallet:
            raise TransactionException("Receiver wallet required for deposit")
        
        self.receiver_wallet.credit(self.amount, self.reference, self.description)
    
    def _execute_withdrawal(self):
        """Execute withdrawal from wallet."""
        if not self.sender_wallet:
            raise TransactionException("Sender wallet required for withdrawal")
        
        self.sender_wallet.debit(self.amount + self.fee, self.reference, self.description)
    
    def _execute_payment(self):
        """Execute payment transaction."""
        if not self.sender_wallet or not self.receiver_wallet:
            raise TransactionException("Both sender and receiver wallets required for payment")
        
        total_amount = self.amount + self.fee
        
        if not self.sender_wallet.can_send(total_amount):
            raise TransactionException("Transaction exceeds wallet limits")
        
        # Debit sender (amount + fee)
        self.sender_wallet.debit(total_amount, self.reference, self.description)
        
        # Credit receiver (amount only, fee goes to platform)
        self.receiver_wallet.credit(self.amount, self.reference, self.description)
    
    def _execute_sponsorship(self):
        """Execute sponsorship transaction."""
        self._execute_transfer()
    
    def _execute_refund(self):
        """Execute refund transaction."""
        if not self.sender_wallet or not self.receiver_wallet:
            raise TransactionException("Both sender and receiver wallets required for refund")
        
        # For refund, sender gives back to receiver
        self.sender_wallet.debit(self.amount, self.reference, self.description)
        self.receiver_wallet.credit(self.amount, self.reference, self.description)
    
    @transaction.atomic
    def cancel(self, reason=''):
        """Cancel pending transaction."""
        if self.status not in [self.PENDING, self.PROCESSING]:
            raise TransactionException("Only pending or processing transactions can be cancelled")
        
        self.status = self.CANCELLED
        self.failure_reason = reason
        self.failed_at = timezone.now()
        self.save(update_fields=['status', 'failure_reason', 'failed_at', 'updated_at'])
    
    @transaction.atomic
    def reverse(self, reason=''):
        """Reverse completed transaction (creates a new reversal transaction)."""
        if self.status != self.COMPLETED:
            raise TransactionException("Only completed transactions can be reversed")
        
        # Create reversal transaction
        reversal = Transaction.objects.create(
            transaction_type=self.REFUND,
            sender_wallet=self.receiver_wallet,
            receiver_wallet=self.sender_wallet,
            amount=self.amount,
            currency=self.currency,
            fee=Decimal('0.00'),
            description=f"Reversal of {self.reference}: {reason}",
            initiated_by=self.initiated_by,
            metadata={
                'original_transaction': str(self.id),
                'original_reference': self.reference,
                'reversal_reason': reason
            }
        )
        
        # Execute reversal
        reversal.execute()
        
        # Mark original as reversed
        self.status = self.REVERSED
        self.save(update_fields=['status', 'updated_at'])
        
        return reversal
    
    def flag_for_review(self, reason=''):
        """Flag transaction for manual review."""
        self.is_flagged = True
        self.flagged_reason = reason
        self.save(update_fields=['is_flagged', 'flagged_reason', 'updated_at'])
    
    def approve_review(self, reviewed_by):
        """Approve flagged transaction."""
        self.is_flagged = False
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewed_by
        self.save(update_fields=['is_flagged', 'reviewed_at', 'reviewed_by', 'updated_at'])
    
    def reconcile(self, reconciled_by):
        """Mark transaction as reconciled."""
        if not self.is_reconciled:
            self.is_reconciled = True
            self.reconciled_at = timezone.now()
            self.reconciled_by = reconciled_by
            self.save(update_fields=['is_reconciled', 'reconciled_at', 'reconciled_by', 'updated_at'])


class FraudRule(BaseModel):
    """
    Fraud detection rules for transaction monitoring.
    """
    name = models.CharField(
        _('rule name'),
        max_length=100,
        unique=True
    )
    description = models.TextField(
        _('description')
    )
    rule_type = models.CharField(
        _('rule type'),
        max_length=50,
        choices=[
            ('AMOUNT_THRESHOLD', _('Amount Threshold')),
            ('VELOCITY', _('Velocity Check')),
            ('PATTERN', _('Pattern Detection')),
            ('GEOLOCATION', _('Geolocation')),
            ('BLACKLIST', _('Blacklist Check')),
        ]
    )
    is_active = models.BooleanField(
        _('is active'),
        default=True
    )
    threshold_value = models.DecimalField(
        _('threshold value'),
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    time_window_minutes = models.IntegerField(
        _('time window (minutes)'),
        null=True,
        blank=True,
        help_text=_('For velocity checks')
    )
    max_occurrences = models.IntegerField(
        _('max occurrences'),
        null=True,
        blank=True,
        help_text=_('For velocity checks')
    )
    fraud_score = models.IntegerField(
        _('fraud score to add'),
        default=10,
        help_text=_('Score to add if rule is triggered')
    )
    auto_block = models.BooleanField(
        _('auto block'),
        default=False,
        help_text=_('Automatically block transaction if rule is triggered')
    )
    
    objects = FraudRuleManager()
    
    class Meta:
        db_table = 'fraud_rules'
        verbose_name = _('Fraud Rule')
        verbose_name_plural = _('Fraud Rules')
    
    def __str__(self):
        return f"{self.name} ({self.rule_type})"


class WalletLedger(UUIDModel, TimestampedModel):
    """
    Immutable ledger for all wallet balance changes.
    Used for auditing and reconciliation.
    """
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name='ledger_entries'
    )
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.PROTECT,
        related_name='ledger_entries',
        null=True,
        blank=True
    )
    entry_type = models.CharField(
        _('entry type'),
        max_length=20,
        choices=[
            ('CREDIT', _('Credit')),
            ('DEBIT', _('Debit')),
        ]
    )
    amount = models.DecimalField(
        _('amount'),
        max_digits=15,
        decimal_places=2
    )
    balance_before = models.DecimalField(
        _('balance before'),
        max_digits=15,
        decimal_places=2
    )
    balance_after = models.DecimalField(
        _('balance after'),
        max_digits=15,
        decimal_places=2
    )
    description = models.TextField(
        _('description'),
        blank=True
    )
    
    class Meta:
        db_table = 'wallet_ledger'
        verbose_name = _('Wallet Ledger Entry')
        verbose_name_plural = _('Wallet Ledger Entries')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wallet', '-created_at']),
            models.Index(fields=['transaction']),
        ]
    
    def __str__(self):
        return f"{self.entry_type} - {self.amount} - {self.wallet}"

