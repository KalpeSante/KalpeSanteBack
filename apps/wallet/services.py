"""
KALPÉ SANTÉ - Wallet Services
Business logic for wallet operations, fraud detection, and reconciliation.
"""

from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from typing import Dict, List, Tuple
from .models import Wallet, Transaction, FraudRule, WalletLedger
from apps.core.exceptions import (
    TransactionException,
    InsufficientFundsException,
    FraudDetectedException,
)


class FraudDetectionService:
    """
    Service for detecting fraudulent transactions using rule-based system.
    """
    
    @staticmethod
    def calculate_fraud_score(transaction: Transaction) -> Tuple[int, List[str]]:
        """
        Calculate fraud score for a transaction.
        Returns (score, reasons)
        """
        score = 0
        reasons = []
        
        # Check all active fraud rules
        rules = FraudRule.objects.active_rules()
        
        for rule in rules:
            triggered, reason = FraudDetectionService._check_rule(transaction, rule)
            if triggered:
                score += rule.fraud_score
                reasons.append(reason)
                
                # Auto-block if configured
                if rule.auto_block:
                    transaction.cancel(reason=f"Auto-blocked by rule: {rule.name}")
                    raise FraudDetectedException(reason)
        
        # Additional checks
        velocity_score, velocity_reasons = FraudDetectionService._check_velocity(transaction)
        score += velocity_score
        reasons.extend(velocity_reasons)
        
        pattern_score, pattern_reasons = FraudDetectionService._check_patterns(transaction)
        score += pattern_score
        reasons.extend(pattern_reasons)
        
        return score, reasons
    
    @staticmethod
    def _check_rule(transaction: Transaction, rule: FraudRule) -> Tuple[bool, str]:
        """Check if transaction triggers a specific rule."""
        if rule.rule_type == 'AMOUNT_THRESHOLD':
            if rule.threshold_value and transaction.amount >= rule.threshold_value:
                return True, f"Amount {transaction.amount} exceeds threshold {rule.threshold_value}"
        
        elif rule.rule_type == 'VELOCITY':
            # Check if too many transactions in time window
            if rule.time_window_minutes and rule.max_occurrences:
                window_start = timezone.now() - timedelta(minutes=rule.time_window_minutes)
                recent_count = Transaction.objects.filter(
                    sender_wallet=transaction.sender_wallet,
                    created_at__gte=window_start,
                    status__in=[Transaction.COMPLETED, Transaction.PROCESSING]
                ).count()
                
                if recent_count >= rule.max_occurrences:
                    return True, f"{recent_count} transactions in {rule.time_window_minutes} minutes"
        
        return False, ""
    
    @staticmethod
    def _check_velocity(transaction: Transaction) -> Tuple[int, List[str]]:
        """Check transaction velocity for anomalies."""
        score = 0
        reasons = []
        
        if not transaction.sender_wallet:
            return score, reasons
        
        # Check transactions in last hour
        one_hour_ago = timezone.now() - timedelta(hours=1)
        recent_transactions = Transaction.objects.filter(
            sender_wallet=transaction.sender_wallet,
            created_at__gte=one_hour_ago,
            status__in=[Transaction.COMPLETED, Transaction.PROCESSING]
        )
        
        count = recent_transactions.count()
        total_amount = recent_transactions.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        
        # More than 5 transactions in 1 hour
        if count >= 5:
            score += 15
            reasons.append(f"High velocity: {count} transactions in 1 hour")
        
        # Total amount exceeds 1,000,000 XOF in 1 hour
        if total_amount >= Decimal('1000000.00'):
            score += 20
            reasons.append(f"High volume: {total_amount} XOF in 1 hour")
        
        return score, reasons
    
    @staticmethod
    def _check_patterns(transaction: Transaction) -> Tuple[int, List[str]]:
        """Check for suspicious patterns."""
        score = 0
        reasons = []
        
        if not transaction.sender_wallet:
            return score, reasons
        
        # Check if this is first transaction from wallet
        previous_transactions = Transaction.objects.filter(
            sender_wallet=transaction.sender_wallet,
            status=Transaction.COMPLETED
        ).count()
        
        if previous_transactions == 0:
            # First transaction with high amount
            if transaction.amount >= Decimal('100000.00'):
                score += 10
                reasons.append("First transaction with high amount")
        
        # Check for round amounts (might be testing)
        if transaction.amount % Decimal('10000.00') == 0:
            score += 5
            reasons.append("Round amount transaction")
        
        # Check if sending to newly created wallet
        if transaction.receiver_wallet:
            receiver_age = (timezone.now() - transaction.receiver_wallet.created_at).days
            if receiver_age < 1 and transaction.amount >= Decimal('50000.00'):
                score += 15
                reasons.append("Large transfer to new wallet")
        
        return score, reasons
    
    @staticmethod
    def evaluate_transaction(transaction: Transaction) -> bool:
        """
        Evaluate transaction for fraud and flag if necessary.
        Returns True if transaction is safe to proceed, False if blocked.
        """
        try:
            score, reasons = FraudDetectionService.calculate_fraud_score(transaction)
            
            transaction.fraud_score = score
            transaction.save(update_fields=['fraud_score', 'updated_at'])
            
            # Flag for manual review if score is high
            if score >= 50:
                transaction.flag_for_review(
                    reason=f"High fraud score ({score}): " + "; ".join(reasons)
                )
                return False
            elif score >= 30:
                transaction.flag_for_review(
                    reason=f"Medium fraud score ({score}): " + "; ".join(reasons)
                )
            
            return True
            
        except FraudDetectedException:
            return False


class ReconciliationService:
    """
    Service for reconciling transactions with external payment providers.
    """
    
    @staticmethod
    @transaction.atomic
    def reconcile_transaction(transaction: Transaction, reconciled_by) -> bool:
        """
        Reconcile a single transaction.
        """
        if transaction.status != Transaction.COMPLETED:
            return False
        
        if transaction.is_reconciled:
            return True
        
        # Perform reconciliation checks
        checks_passed = ReconciliationService._verify_transaction(transaction)
        
        if checks_passed:
            transaction.reconcile(reconciled_by)
            return True
        
        return False
    
    @staticmethod
    def _verify_transaction(transaction: Transaction) -> bool:
        """Verify transaction integrity."""
        # Check if transaction exists in ledger
        ledger_entries = WalletLedger.objects.filter(transaction=transaction)
        
        if not ledger_entries.exists():
            return False
        
        # Verify balance changes match transaction amount
        total_changes = ledger_entries.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        # For transfer, total should be 0 (debit + credit)
        if transaction.transaction_type == Transaction.TRANSFER:
            if abs(total_changes) > Decimal('0.01'):  # Allow for rounding
                return False
        
        return True
    
    @staticmethod
    @transaction.atomic
    def reconcile_daily_transactions(date, reconciled_by):
        """
        Reconcile all completed transactions for a specific date.
        """
        transactions = Transaction.objects.filter(
            created_at__date=date,
            status=Transaction.COMPLETED,
            is_reconciled=False
        )
        
        results = {
            'total': transactions.count(),
            'reconciled': 0,
            'failed': 0,
            'errors': []
        }
        
        for txn in transactions:
            try:
                if ReconciliationService.reconcile_transaction(txn, reconciled_by):
                    results['reconciled'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'transaction_id': str(txn.id),
                        'reference': txn.reference,
                        'error': 'Verification failed'
                    })
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'transaction_id': str(txn.id),
                    'reference': txn.reference,
                    'error': str(e)
                })
        
        return results


class WalletService:
    """
    Service for wallet operations.
    """
    
    @staticmethod
    @transaction.atomic
    def transfer(sender_wallet: Wallet, receiver_wallet: Wallet, amount: Decimal,
                 description: str = '', initiated_by=None, check_fraud: bool = True) -> Transaction:
        """
        Transfer funds between wallets with fraud detection.
        """
        # Create transaction
        txn = Transaction.objects.create_transfer(
            sender_wallet=sender_wallet,
            receiver_wallet=receiver_wallet,
            amount=amount,
            description=description,
            initiated_by=initiated_by
        )
        
        # Check for fraud if enabled
        if check_fraud:
            is_safe = FraudDetectionService.evaluate_transaction(txn)
            if not is_safe:
                raise FraudDetectedException(
                    f"Transaction flagged for fraud review: {txn.flagged_reason}"
                )
        
        # Execute transaction
        try:
            txn.execute()
            
            # Create ledger entries
            WalletService._create_ledger_entries(txn)
            
            return txn
        except Exception as e:
            raise TransactionException(f"Transfer failed: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def deposit(receiver_wallet: Wallet, amount: Decimal, description: str = '',
                external_reference: str = '', initiated_by=None) -> Transaction:
        """
        Deposit funds to wallet.
        """
        txn = Transaction.objects.create_deposit(
            receiver_wallet=receiver_wallet,
            amount=amount,
            description=description,
            external_reference=external_reference,
            initiated_by=initiated_by
        )
        
        try:
            txn.execute()
            WalletService._create_ledger_entries(txn)
            return txn
        except Exception as e:
            raise TransactionException(f"Deposit failed: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def withdraw(sender_wallet: Wallet, amount: Decimal, fee: Decimal = Decimal('0.00'),
                 description: str = '', external_reference: str = '', initiated_by=None) -> Transaction:
        """
        Withdraw funds from wallet.
        """
        txn = Transaction.objects.create_withdrawal(
            sender_wallet=sender_wallet,
            amount=amount,
            fee=fee,
            description=description,
            external_reference=external_reference,
            initiated_by=initiated_by
        )
        
        try:
            txn.execute()
            WalletService._create_ledger_entries(txn)
            return txn
        except Exception as e:
            raise TransactionException(f"Withdrawal failed: {str(e)}")
    
    @staticmethod
    def _create_ledger_entries(transaction: Transaction):
        """Create ledger entries for transaction."""
        # Debit entry
        if transaction.sender_wallet:
            WalletLedger.objects.create(
                wallet=transaction.sender_wallet,
                transaction=transaction,
                entry_type='DEBIT',
                amount=transaction.amount + transaction.fee,
                balance_before=transaction.sender_wallet.balance + (transaction.amount + transaction.fee),
                balance_after=transaction.sender_wallet.balance,
                description=transaction.description
            )
        
        # Credit entry
        if transaction.receiver_wallet:
            WalletLedger.objects.create(
                wallet=transaction.receiver_wallet,
                transaction=transaction,
                entry_type='CREDIT',
                amount=transaction.amount,
                balance_before=transaction.receiver_wallet.balance - transaction.amount,
                balance_after=transaction.receiver_wallet.balance,
                description=transaction.description
            )
    
    @staticmethod
    def get_wallet_balance(wallet: Wallet) -> Dict:
        """Get detailed wallet balance information."""
        return {
            'balance': wallet.balance,
            'currency': wallet.currency,
            'daily_spent': wallet.get_daily_spent(),
            'daily_limit': wallet.daily_limit,
            'daily_remaining': wallet.daily_limit - wallet.get_daily_spent(),
            'monthly_spent': wallet.get_monthly_spent(),
            'monthly_limit': wallet.monthly_limit,
            'monthly_remaining': wallet.monthly_limit - wallet.get_monthly_spent(),
            'is_active': wallet.is_active,
            'is_locked': wallet.is_locked,
        }
    
    @staticmethod
    def get_transaction_history(wallet: Wallet, days: int = 30) -> Dict:
        """Get transaction history for wallet."""
        since = timezone.now() - timedelta(days=days)
        
        sent = Transaction.objects.filter(
            sender_wallet=wallet,
            created_at__gte=since
        ).order_by('-created_at')
        
        received = Transaction.objects.filter(
            receiver_wallet=wallet,
            created_at__gte=since
        ).order_by('-created_at')
        
        return {
            'sent_transactions': sent,
            'received_transactions': received,
            'sent_count': sent.count(),
            'received_count': received.count(),
            'sent_total': sent.filter(status=Transaction.COMPLETED).aggregate(
                Sum('amount')
            )['amount__sum'] or Decimal('0.00'),
            'received_total': received.filter(status=Transaction.COMPLETED).aggregate(
                Sum('amount')
            )['amount__sum'] or Decimal('0.00'),
        }


