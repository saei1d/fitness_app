# urls.py
from django.urls import path
from .pending_purchase import CreatePendingPurchaseView
from .purchase import FinalizePurchaseView, VerifyPurchaseView
from .withdraw_request import WithdrawRequestView
from .crud_transaction import TransactionListCreateView, TransactionDetailView
from .wallet import WalletDetailView, WalletListView

urlpatterns = [
    path('pending/<int:package_id>/', CreatePendingPurchaseView.as_view(), name='pending-purchase-package'),
    path('final-purchase/', FinalizePurchaseView.as_view(), name='final-purchase-package'),
    path('verify-by-gym/', VerifyPurchaseView.as_view(), name='verify-purchase'),
    path('owner/withdraw-request/', WithdrawRequestView.as_view(), name='withdraw-request'),
    path('transactions/', TransactionListCreateView.as_view(), name='transactions-list-create'),
    path('transactions/<int:pk>/', TransactionDetailView.as_view(), name='transactions-detail'),
    path('wallet/', WalletListView.as_view(), name='wallet-list'),
    path('wallet/<int:pk>/', WalletDetailView.as_view(), name='wallet-detail')
]
