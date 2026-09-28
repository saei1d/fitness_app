# urls.py
from django.urls import path
from .members import GymMemberListView
from .purchase_history import PurchaseHistoryView
from .pending_purchase import CreatePendingPurchaseView, CreateTrainerPendingPurchaseView
from .purchase import FinalizePurchaseView, PaymentCallbackView, VerifyPurchaseView
from .withdraw_request import WithdrawRequestView
from .trainer_withdraw_request import TrainerWithdrawRequestView
from .trainer_transactions import TrainerTransactionListView
from .crud_transaction import TransactionListCreateView, TransactionDetailView
from .wallet import WalletDetailView, WalletListView, TrainerWalletListView

urlpatterns = [
    path('pending/<int:package_id>/', CreatePendingPurchaseView.as_view(), name='pending-purchase-package'),
    path('pending/trainer/<int:trainer_package_id>/', CreateTrainerPendingPurchaseView.as_view(), name='pending-purchase-trainer-package'),
    path('final-purchase/', FinalizePurchaseView.as_view(), name='final-purchase-package'),
    path('payment/callback/', PaymentCallbackView.as_view(), name='payment-callback'),
    path('verify-by-gym/', VerifyPurchaseView.as_view(), name='verify-purchase'),
    path('members/', GymMemberListView.as_view(), name='gym-member-list'),
    path('purchase-history/', PurchaseHistoryView.as_view(), name='purchase-history'),
    path('owner/withdraw-request/', WithdrawRequestView.as_view(), name='withdraw-request'),
    path('trainer/withdraw-request/', TrainerWithdrawRequestView.as_view(), name='trainer-withdraw-request'),
    path('transactions/', TransactionListCreateView.as_view(), name='transactions-list-create'),
    path('transactions/<int:pk>/', TransactionDetailView.as_view(), name='transactions-detail'),
    path('trainer/transactions/', TrainerTransactionListView.as_view(), name='trainer-transactions'),
    path('wallet/', WalletListView.as_view(), name='wallet-list'),
    path('wallet/<int:pk>/', WalletDetailView.as_view(), name='wallet-detail'),
    path('trainer/wallet/', TrainerWalletListView.as_view(), name='trainer-wallet'),
]
