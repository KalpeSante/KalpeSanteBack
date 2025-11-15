"""
KALPÉ SANTÉ - Wallet Serializers
Serializers for wallet API endpoints.
"""

from rest_framework import serializers
from decimal import Decimal
from .models import Wallet, Transaction, FraudRule, WalletLedger
from apps.users.serializers import UserSerializer


class WalletSerializer(serializers.ModelSerializer):
    """Serializer for Wallet model."""
    
    user = UserSerializer(read_only=True)
    daily_spent = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        read_only=True
    )
    daily_remaining = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        read_only=True
    )
    monthly_spent = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        read_only=True
    )
    monthly_remaining = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        read_only=True
    )
    
    class Meta:
        model = Wallet
        fields = [
            'id', 'user', 'balance', 'currency', 'is_active', 'is_locked',
            'locked_reason', 'locked_at', 'daily_limit', 'monthly_limit',
            'daily_spent', 'daily_remaining', 'monthly_spent', 'monthly_remaining',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'balance', 'is_locked', 'locked_reason', 'locked_at',
            'created_at', 'updated_at'
        ]
    
    def to_representation(self, instance):
        """Add computed fields to serialization."""
        representation = super().to_representation(instance)
        representation['daily_spent'] = instance.get_daily_spent()
        representation['daily_remaining'] = instance.daily_limit - instance.get_daily_spent()
        representation['monthly_spent'] = instance.get_monthly_spent()
        representation['monthly_remaining'] = instance.monthly_limit - instance.get_monthly_spent()
        return representation


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for Transaction model."""
    
    sender_wallet_id = serializers.UUIDField(source='sender_wallet.id', read_only=True)
    receiver_wallet_id = serializers.UUIDField(source='receiver_wallet.id', read_only=True)
    sender_email = serializers.EmailField(source='sender_wallet.user.email', read_only=True)
    receiver_email = serializers.EmailField(source='receiver_wallet.user.email', read_only=True)
    initiated_by_email = serializers.EmailField(source='initiated_by.email', read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'reference', 'transaction_type', 'status', 'amount', 'currency',
            'fee', 'description', 'sender_wallet_id', 'receiver_wallet_id',
            'sender_email', 'receiver_email', 'external_reference', 'metadata',
            'initiated_by_email', 'fraud_score', 'is_flagged', 'flagged_reason',
            'is_reconciled', 'reconciled_at', 'completed_at', 'failed_at',
            'failure_reason', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'reference', 'status', 'fraud_score', 'is_flagged',
            'flagged_reason', 'is_reconciled', 'reconciled_at', 'completed_at',
            'failed_at', 'failure_reason', 'created_at', 'updated_at'
        ]


class TransferSerializer(serializers.Serializer):
    """Serializer for transfer requests."""
    
    receiver_email = serializers.EmailField(
        required=True,
        help_text="Email of the recipient"
    )
    amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('1.00'),
        required=True,
        help_text="Amount to transfer (min 1 XOF)"
    )
    description = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Transfer description"
    )
    
    def validate_amount(self, value):
        """Validate transfer amount."""
        if value < Decimal('1.00'):
            raise serializers.ValidationError("Amount must be at least 1 XOF")
        if value > Decimal('10000000.00'):  # 10 million XOF
            raise serializers.ValidationError("Amount exceeds maximum limit")
        return value
    
    def validate_receiver_email(self, value):
        """Validate receiver exists and has active wallet."""
        from apps.users.models import User
        
        try:
            user = User.objects.get(email=value)
            if not hasattr(user, 'wallet'):
                raise serializers.ValidationError("Receiver does not have a wallet")
            if not user.wallet.is_active:
                raise serializers.ValidationError("Receiver wallet is not active")
            if user.wallet.is_locked:
                raise serializers.ValidationError("Receiver wallet is locked")
        except User.DoesNotExist:
            raise serializers.ValidationError("Receiver not found")
        
        return value


class DepositSerializer(serializers.Serializer):
    """Serializer for deposit requests."""
    
    amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('100.00'),
        required=True,
        help_text="Amount to deposit (min 100 XOF)"
    )
    payment_method = serializers.ChoiceField(
        choices=['ORANGE_MONEY', 'WAVE', 'BANK_CARD', 'BANK_TRANSFER'],
        required=True,
        help_text="Payment method"
    )
    phone_number = serializers.CharField(
        max_length=15,
        required=False,
        help_text="Phone number for mobile money"
    )
    description = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True
    )
    
    def validate(self, attrs):
        """Validate deposit data."""
        payment_method = attrs.get('payment_method')
        phone_number = attrs.get('phone_number')
        
        # Phone number required for mobile money
        if payment_method in ['ORANGE_MONEY', 'WAVE'] and not phone_number:
            raise serializers.ValidationError({
                'phone_number': 'Phone number required for mobile money'
            })
        
        return attrs


class WithdrawalSerializer(serializers.Serializer):
    """Serializer for withdrawal requests."""
    
    amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('1000.00'),
        required=True,
        help_text="Amount to withdraw (min 1000 XOF)"
    )
    withdrawal_method = serializers.ChoiceField(
        choices=['ORANGE_MONEY', 'WAVE', 'BANK_TRANSFER'],
        required=True,
        help_text="Withdrawal method"
    )
    phone_number = serializers.CharField(
        max_length=15,
        required=False,
        help_text="Phone number for mobile money"
    )
    bank_account = serializers.CharField(
        max_length=50,
        required=False,
        help_text="Bank account number"
    )
    description = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True
    )
    
    def validate(self, attrs):
        """Validate withdrawal data."""
        method = attrs.get('withdrawal_method')
        phone_number = attrs.get('phone_number')
        bank_account = attrs.get('bank_account')
        
        if method in ['ORANGE_MONEY', 'WAVE'] and not phone_number:
            raise serializers.ValidationError({
                'phone_number': 'Phone number required for mobile money'
            })
        
        if method == 'BANK_TRANSFER' and not bank_account:
            raise serializers.ValidationError({
                'bank_account': 'Bank account required for bank transfer'
            })
        
        return attrs


class WalletLedgerSerializer(serializers.ModelSerializer):
    """Serializer for WalletLedger model."""
    
    transaction_reference = serializers.CharField(
        source='transaction.reference',
        read_only=True
    )
    
    class Meta:
        model = WalletLedger
        fields = [
            'id', 'wallet', 'transaction', 'transaction_reference',
            'entry_type', 'amount', 'balance_before', 'balance_after',
            'description', 'created_at'
        ]
        read_only_fields = fields


class FraudRuleSerializer(serializers.ModelSerializer):
    """Serializer for FraudRule model."""
    
    class Meta:
        model = FraudRule
        fields = [
            'id', 'name', 'description', 'rule_type', 'is_active',
            'threshold_value', 'time_window_minutes', 'max_occurrences',
            'fraud_score', 'auto_block', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TransactionStatsSerializer(serializers.Serializer):
    """Serializer for transaction statistics."""
    
    total_count = serializers.IntegerField()
    completed_count = serializers.IntegerField()
    failed_count = serializers.IntegerField()
    total_volume = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_fees = serializers.DecimalField(max_digits=15, decimal_places=2)
    flagged_count = serializers.IntegerField()


