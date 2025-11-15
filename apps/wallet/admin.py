"""
KALPÉ SANTÉ - Wallet Admin
Django admin configuration for wallet models.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Wallet, Transaction, FraudRule, WalletLedger


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    """Admin interface for Wallet model."""
    
    list_display = [
        'user_email', 'balance', 'currency', 'is_active', 'is_locked',
        'daily_spent_display', 'created_at'
    ]
    list_filter = ['is_active', 'is_locked', 'currency', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at', 'locked_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'balance', 'currency')
        }),
        ('Status', {
            'fields': ('is_active', 'is_locked', 'locked_reason', 'locked_at', 'locked_by')
        }),
        ('Limits', {
            'fields': ('daily_limit', 'monthly_limit')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'
    
    def daily_spent_display(self, obj):
        spent = obj.get_daily_spent()
        limit = obj.daily_limit
        percentage = (spent / limit * 100) if limit > 0 else 0
        
        color = 'green' if percentage < 50 else 'orange' if percentage < 80 else 'red'
        return format_html(
            '<span style="color: {};">{} / {} ({:.1f}%)</span>',
            color, spent, limit, percentage
        )
    daily_spent_display.short_description = 'Daily Spent'
    
    actions = ['lock_wallets', 'unlock_wallets']
    
    def lock_wallets(self, request, queryset):
        """Lock selected wallets."""
        for wallet in queryset:
            wallet.lock(reason="Locked by admin", locked_by=request.user)
        self.message_user(request, f"{queryset.count()} wallets locked successfully")
    lock_wallets.short_description = "Lock selected wallets"
    
    def unlock_wallets(self, request, queryset):
        """Unlock selected wallets."""
        for wallet in queryset:
            wallet.unlock()
        self.message_user(request, f"{queryset.count()} wallets unlocked successfully")
    unlock_wallets.short_description = "Unlock selected wallets"


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Admin interface for Transaction model."""
    
    list_display = [
        'reference', 'transaction_type', 'amount', 'currency', 'status',
        'fraud_score_display', 'is_flagged', 'is_reconciled', 'created_at'
    ]
    list_filter = [
        'transaction_type', 'status', 'is_flagged', 'is_reconciled',
        'created_at', 'currency'
    ]
    search_fields = [
        'reference', 'external_reference', 'description',
        'sender_wallet__user__email', 'receiver_wallet__user__email'
    ]
    readonly_fields = [
        'reference', 'fraud_score', 'created_at', 'updated_at',
        'completed_at', 'failed_at', 'reconciled_at'
    ]
    
    fieldsets = (
        ('Transaction Details', {
            'fields': (
                'reference', 'transaction_type', 'status', 'amount',
                'currency', 'fee', 'description'
            )
        }),
        ('Parties', {
            'fields': ('sender_wallet', 'receiver_wallet', 'initiated_by')
        }),
        ('External', {
            'fields': ('external_reference', 'metadata')
        }),
        ('Fraud Detection', {
            'fields': (
                'fraud_score', 'is_flagged', 'flagged_reason',
                'reviewed_at', 'reviewed_by'
            )
        }),
        ('Reconciliation', {
            'fields': ('is_reconciled', 'reconciled_at', 'reconciled_by')
        }),
        ('Status Details', {
            'fields': (
                'completed_at', 'failed_at', 'failure_reason'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def fraud_score_display(self, obj):
        """Display fraud score with color coding."""
        score = obj.fraud_score
        if score == 0:
            color = 'green'
        elif score < 30:
            color = 'blue'
        elif score < 50:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, score
        )
    fraud_score_display.short_description = 'Fraud Score'
    fraud_score_display.admin_order_field = 'fraud_score'
    
    actions = ['approve_flagged', 'reconcile_transactions']
    
    def approve_flagged(self, request, queryset):
        """Approve flagged transactions."""
        for txn in queryset.filter(is_flagged=True):
            txn.approve_review(reviewed_by=request.user)
        self.message_user(request, f"{queryset.count()} transactions approved")
    approve_flagged.short_description = "Approve flagged transactions"
    
    def reconcile_transactions(self, request, queryset):
        """Reconcile selected transactions."""
        from .services import ReconciliationService
        
        count = 0
        for txn in queryset.filter(status=Transaction.COMPLETED, is_reconciled=False):
            if ReconciliationService.reconcile_transaction(txn, request.user):
                count += 1
        
        self.message_user(request, f"{count} transactions reconciled successfully")
    reconcile_transactions.short_description = "Reconcile selected transactions"


@admin.register(FraudRule)
class FraudRuleAdmin(admin.ModelAdmin):
    """Admin interface for FraudRule model."""
    
    list_display = [
        'name', 'rule_type', 'is_active', 'fraud_score',
        'threshold_value', 'auto_block', 'created_at'
    ]
    list_filter = ['rule_type', 'is_active', 'auto_block', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'rule_type', 'is_active')
        }),
        ('Rule Configuration', {
            'fields': (
                'threshold_value', 'time_window_minutes',
                'max_occurrences', 'fraud_score', 'auto_block'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_rules', 'deactivate_rules']
    
    def activate_rules(self, request, queryset):
        """Activate selected rules."""
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} rules activated")
    activate_rules.short_description = "Activate selected rules"
    
    def deactivate_rules(self, request, queryset):
        """Deactivate selected rules."""
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} rules deactivated")
    deactivate_rules.short_description = "Deactivate selected rules"


@admin.register(WalletLedger)
class WalletLedgerAdmin(admin.ModelAdmin):
    """Admin interface for WalletLedger model (read-only)."""
    
    list_display = [
        'wallet_user', 'entry_type', 'amount', 'balance_before',
        'balance_after', 'transaction_ref', 'created_at'
    ]
    list_filter = ['entry_type', 'created_at']
    search_fields = [
        'wallet__user__email', 'transaction__reference', 'description'
    ]
    readonly_fields = [
        'wallet', 'transaction', 'entry_type', 'amount',
        'balance_before', 'balance_after', 'description', 'created_at'
    ]
    
    def wallet_user(self, obj):
        return obj.wallet.user.email
    wallet_user.short_description = 'Wallet User'
    wallet_user.admin_order_field = 'wallet__user__email'
    
    def transaction_ref(self, obj):
        return obj.transaction.reference if obj.transaction else 'N/A'
    transaction_ref.short_description = 'Transaction Ref'
    
    def has_add_permission(self, request):
        """Ledger entries cannot be added manually."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Ledger entries cannot be deleted."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Ledger entries cannot be modified."""
        return False
