"""
KALPÉ SANTÉ - Wallet Views
API endpoints for wallet operations, transactions, and fraud management.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction as db_transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from apps.core.permissions import IsOwner
from apps.core.exceptions import (
    TransactionException,
    InsufficientFundsException,
    FraudDetectedException,
)
from .models import Wallet, Transaction, FraudRule, WalletLedger
from .serializers import (
    WalletSerializer,
    TransactionSerializer,
    TransferSerializer,
    DepositSerializer,
    WithdrawalSerializer,
    WalletLedgerSerializer,
    FraudRuleSerializer,
    TransactionStatsSerializer,
)
from .services import WalletService, FraudDetectionService, ReconciliationService


@extend_schema_view(
    list=extend_schema(tags=['Wallet'], description='List user wallets'),
    retrieve=extend_schema(tags=['Wallet'], description='Get wallet details'),
)
class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for wallet management.
    Users can only view their own wallet.
    """
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter wallets by user."""
        if self.request.user.is_staff:
            return Wallet.objects.all()
        return Wallet.objects.filter(user=self.request.user)
    
    @extend_schema(
        tags=['Wallet'],
        description='Get current user wallet',
        responses={200: WalletSerializer}
    )
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user's wallet."""
        wallet, created = Wallet.objects.get_or_create_for_user(request.user)
        serializer = self.get_serializer(wallet)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Wallet'],
        description='Get wallet balance details',
        responses={200: WalletSerializer}
    )
    @action(detail=True, methods=['get'])
    def balance(self, request, pk=None):
        """Get detailed balance information."""
        wallet = self.get_object()
        balance_info = WalletService.get_wallet_balance(wallet)
        return Response(balance_info)
    
    @extend_schema(
        tags=['Wallet'],
        description='Get wallet transaction history',
        parameters=[
            OpenApiParameter('days', int, description='Number of days to look back (default 30)')
        ]
    )
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """Get transaction history for wallet."""
        wallet = self.get_object()
        days = int(request.query_params.get('days', 30))
        
        history = WalletService.get_transaction_history(wallet, days)
        
        return Response({
            'wallet_id': str(wallet.id),
            'sent_transactions': TransactionSerializer(history['sent_transactions'], many=True).data,
            'received_transactions': TransactionSerializer(history['received_transactions'], many=True).data,
            'summary': {
                'sent_count': history['sent_count'],
                'received_count': history['received_count'],
                'sent_total': str(history['sent_total']),
                'received_total': str(history['received_total']),
            }
        })
    
    @extend_schema(
        tags=['Wallet'],
        description='Get wallet ledger entries',
        parameters=[
            OpenApiParameter('limit', int, description='Number of entries to return (default 50)')
        ]
    )
    @action(detail=True, methods=['get'])
    def ledger(self, request, pk=None):
        """Get ledger entries for wallet."""
        wallet = self.get_object()
        limit = int(request.query_params.get('limit', 50))
        
        ledger_entries = WalletLedger.objects.filter(
            wallet=wallet
        ).order_by('-created_at')[:limit]
        
        serializer = WalletLedgerSerializer(ledger_entries, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(tags=['Transactions'], description='List transactions'),
    retrieve=extend_schema(tags=['Transactions'], description='Get transaction details'),
)
class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for transaction management.
    """
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'transaction_type', 'is_flagged', 'is_reconciled']
    search_fields = ['reference', 'description', 'external_reference']
    ordering_fields = ['created_at', 'amount', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter transactions by user."""
        user = self.request.user
        
        if user.is_staff:
            return Transaction.objects.all()
        
        # Return transactions where user is sender or receiver
        return Transaction.objects.filter(
            db_transaction.Q(sender_wallet__user=user) | 
            db_transaction.Q(receiver_wallet__user=user)
        ).distinct()
    
    @extend_schema(
        tags=['Transactions'],
        request=TransferSerializer,
        responses={201: TransactionSerializer},
        description='Transfer funds to another user'
    )
    @action(detail=False, methods=['post'])
    def transfer(self, request):
        """
        Transfer funds from current user's wallet to another user's wallet.
        """
        serializer = TransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get sender wallet
        sender_wallet, _ = Wallet.objects.get_or_create_for_user(request.user)
        
        # Get receiver wallet
        from apps.users.models import User
        receiver_user = User.objects.get(email=serializer.validated_data['receiver_email'])
        receiver_wallet, _ = Wallet.objects.get_or_create_for_user(receiver_user)
        
        try:
            # Execute transfer with fraud detection
            txn = WalletService.transfer(
                sender_wallet=sender_wallet,
                receiver_wallet=receiver_wallet,
                amount=serializer.validated_data['amount'],
                description=serializer.validated_data.get('description', ''),
                initiated_by=request.user,
                check_fraud=True
            )
            
            return Response(
                {
                    'message': 'Transfer completed successfully',
                    'transaction': TransactionSerializer(txn).data
                },
                status=status.HTTP_201_CREATED
            )
            
        except InsufficientFundsException as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except FraudDetectedException as e:
            return Response(
                {'error': 'Transaction flagged for fraud review', 'details': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except TransactionException as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        tags=['Transactions'],
        request=DepositSerializer,
        responses={201: TransactionSerializer},
        description='Deposit funds to wallet'
    )
    @action(detail=False, methods=['post'])
    def deposit(self, request):
        """
        Initiate deposit to user's wallet.
        In production, this would integrate with payment providers.
        """
        serializer = DepositSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        wallet, _ = Wallet.objects.get_or_create_for_user(request.user)
        
        try:
            # Create pending deposit transaction
            # In production, this would be completed after payment provider confirms
            txn = WalletService.deposit(
                receiver_wallet=wallet,
                amount=serializer.validated_data['amount'],
                description=f"Deposit via {serializer.validated_data['payment_method']}",
                external_reference=f"EXT-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                initiated_by=request.user
            )
            
            return Response(
                {
                    'message': 'Deposit initiated successfully',
                    'transaction': TransactionSerializer(txn).data,
                    'payment_instructions': {
                        'method': serializer.validated_data['payment_method'],
                        'amount': str(serializer.validated_data['amount']),
                        'reference': txn.reference,
                    }
                },
                status=status.HTTP_201_CREATED
            )
            
        except TransactionException as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        tags=['Transactions'],
        request=WithdrawalSerializer,
        responses={201: TransactionSerializer},
        description='Withdraw funds from wallet'
    )
    @action(detail=False, methods=['post'])
    def withdraw(self, request):
        """
        Initiate withdrawal from user's wallet.
        """
        serializer = WithdrawalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        wallet, _ = Wallet.objects.get_or_create_for_user(request.user)
        
        # Calculate withdrawal fee (1% minimum 100 XOF, maximum 5000 XOF)
        amount = serializer.validated_data['amount']
        fee = max(amount * 0.01, 100)
        fee = min(fee, 5000)
        
        try:
            txn = WalletService.withdraw(
                sender_wallet=wallet,
                amount=amount,
                fee=fee,
                description=f"Withdrawal via {serializer.validated_data['withdrawal_method']}",
                external_reference=f"WTH-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                initiated_by=request.user
            )
            
            return Response(
                {
                    'message': 'Withdrawal initiated successfully',
                    'transaction': TransactionSerializer(txn).data,
                    'withdrawal_details': {
                        'method': serializer.validated_data['withdrawal_method'],
                        'amount': str(amount),
                        'fee': str(fee),
                        'total': str(amount + fee),
                    }
                },
                status=status.HTTP_201_CREATED
            )
            
        except InsufficientFundsException as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except TransactionException as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        tags=['Transactions'],
        description='Cancel a pending transaction',
        responses={200: TransactionSerializer}
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a pending transaction."""
        txn = self.get_object()
        
        # Only the initiator or admin can cancel
        if txn.initiated_by != request.user and not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            txn.cancel(reason=request.data.get('reason', 'Cancelled by user'))
            return Response(
                {
                    'message': 'Transaction cancelled successfully',
                    'transaction': TransactionSerializer(txn).data
                }
            )
        except TransactionException as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        tags=['Transactions'],
        description='Get transaction statistics',
        parameters=[
            OpenApiParameter('date', str, description='Date in YYYY-MM-DD format (default today)')
        ],
        responses={200: TransactionStatsSerializer}
    )
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def stats(self, request):
        """Get transaction statistics (admin only)."""
        date_str = request.query_params.get('date')
        if date_str:
            date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            date = timezone.now().date()
        
        stats = Transaction.objects.get_daily_stats(date)
        serializer = TransactionStatsSerializer(stats)
        
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Transactions'],
        description='Reconcile a transaction (admin only)',
        responses={200: TransactionSerializer}
    )
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def reconcile(self, request, pk=None):
        """Reconcile a completed transaction (admin only)."""
        txn = self.get_object()
        
        try:
            success = ReconciliationService.reconcile_transaction(txn, request.user)
            if success:
                return Response(
                    {
                        'message': 'Transaction reconciled successfully',
                        'transaction': TransactionSerializer(txn).data
                    }
                )
            else:
                return Response(
                    {'error': 'Reconciliation failed'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema_view(
    list=extend_schema(tags=['Fraud'], description='List fraud rules (admin only)'),
    create=extend_schema(tags=['Fraud'], description='Create fraud rule (admin only)'),
    retrieve=extend_schema(tags=['Fraud'], description='Get fraud rule details (admin only)'),
    update=extend_schema(tags=['Fraud'], description='Update fraud rule (admin only)'),
    destroy=extend_schema(tags=['Fraud'], description='Delete fraud rule (admin only)'),
)
class FraudRuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for fraud rule management (admin only).
    """
    queryset = FraudRule.objects.all()
    serializer_class = FraudRuleSerializer
    permission_classes = [permissions.IsAdminUser]
    filterset_fields = ['rule_type', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['-created_at']


