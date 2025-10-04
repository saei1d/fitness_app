# urls.py
from django.urls import path
from .purchase import PurchasePackageView

urlpatterns = [
    path('purchase/<int:package_id>/', PurchasePackageView.as_view(), name='purchase-package'),
]