from django.urls import path
from .wallet import *
from .withdraw_request import *


urlpatterns = [
    # لیست همه کیف پول‌ها
    path('wallet/', AdminWalletListView.as_view(), name='admin-wallet-list'),
        
    # به‌روزرسانی موجودی کیف پول
    path('wallets/<int:pk>/balance/', AdminWalletBalanceUpdateView.as_view(), name='admin-wallet-balance-update'),
    
    # تراکنش‌های کیف پول
    path('wallets/<int:pk>/transactions/', AdminWalletTransactionsView.as_view(), name='admin-wallet-transactions'),
    
    # جستجوی کیف پول
    path('wallets/search/', AdminWalletSearchView.as_view(), name='admin-wallet-search'),
    
    # لیست همه خریدها
    path('purchases/', AdminPurchaseListView.as_view(), name='admin-purchase-list'),
    
    # جزئیات خرید خاص
    path('purchases/<int:pk>/', AdminPurchaseDetailView.as_view(), name='admin-purchase-detail'),
    
    # تراکنش‌های کیف پول ادمین
    path('wallet/transactions/', AdminWalletTransactionsView.as_view(), name='admin-wallet-transactions'),

    path('withdraw-request/<int:pk>/', AdminWithdrawRequestView.as_view(), name='admin-withdraw-request'),
    
    # لیست همه درخواست‌های برداشت
    path('withdraw-requests/', AdminWithdrawRequestListView.as_view(), name='admin-withdraw-request-list'),
    
    
    # جزئیات درخواست برداشت خاص
    path('withdraw-requests-detail/<int:pk>/', AdminWithdrawRequestDetailView.as_view(), name='admin-withdraw-request-detail'),

]
