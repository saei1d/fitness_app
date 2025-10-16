# urls.py
from django.urls import path
from .pending_purchase import CreatePendingPurchaseView
from .purchase import FinalizePurchaseView, VerifyPurchaseView
from .withdraw_request import WithdrawRequestView, AdminWithdrawRequestView
from .crud_transaction import TransactionListCreateView, TransactionDetailView

urlpatterns = [
    path('pending/<int:package_id>/', CreatePendingPurchaseView.as_view(), name='pending-purchase-package'),
    path('final/', FinalizePurchaseView.as_view(), name='final-purchase-package'),
    path('verify/', VerifyPurchaseView.as_view(), name='verify-purchase'),
    path('owner/withdraw-request/', WithdrawRequestView.as_view(), name='withdraw-request'),
    path('admin/withdraw-request/<int:pk>/', AdminWithdrawRequestView.as_view(), name='admin-withdraw-request'),
    path('transactions/', TransactionListCreateView.as_view(), name='transactions-list-create'),
    path('transactions/<int:pk>/', TransactionDetailView.as_view(), name='transactions-detail'),
]
