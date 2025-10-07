# urls.py
from django.urls import path
from .pending_purchase import CreatePendingPurchaseView
from .purchase import FinalizePurchaseView

urlpatterns = [
    path('pending/<int:package_id>/', CreatePendingPurchaseView.as_view(), name='pending-purchase-package'),
    path('final/', FinalizePurchaseView.as_view(), name='final-purchase-package'),
]
