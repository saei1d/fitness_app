from django.urls import path
from .wallet import *
from .withdraw_request import *
from .stats import MonthlyStatsAPIView, GymGenderSalesAPIView


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

    # درخواست‌های برداشت مربی
    path('trainer-withdraw-request/<int:pk>/', AdminTrainerWithdrawRequestView.as_view(), name='admin-trainer-withdraw-request'),

    # لیست همه درخواست‌های برداشت مربی
    path('trainer-withdraw-requests/', AdminTrainerWithdrawRequestListView.as_view(), name='admin-trainer-withdraw-request-list'),

    # جزئیات درخواست برداشت مربی خاص
    path('trainer-withdraw-requests-detail/<int:pk>/', AdminTrainerWithdrawRequestDetailView.as_view(), name='admin-trainer-withdraw-request-detail'),

    # کیف پول‌های مربی
    path('trainer-wallets/', AdminTrainerWalletListView.as_view(), name='admin-trainer-wallet-list'),

    # جزئیات کیف پول مربی
    path('trainer-wallets/<int:pk>/', AdminTrainerWalletDetailView.as_view(), name='admin-trainer-wallet-detail'),

    # به‌روزرسانی موجودی کیف پول مربی
    path('trainer-wallets/<int:pk>/balance/', AdminTrainerWalletBalanceUpdateView.as_view(), name='admin-trainer-wallet-balance-update'),

    # تراکنش‌های کیف پول مربی
    path('trainer-wallets/<int:pk>/transactions/', AdminTrainerWalletTransactionsView.as_view(), name='admin-trainer-wallet-transactions'),

    # جستجوی کیف پول مربی
    path('trainer-wallets/search/', AdminTrainerWalletSearchView.as_view(), name='admin-trainer-wallet-search'),

    # آمار ماهانه - باشگاه و مربی برتر
    path('monthly-stats/', MonthlyStatsAPIView.as_view(), name='admin-monthly-stats'),

    # آمار فروش بر اساس gender در یک ماه گذشته
    path('gym-gender-sales/', GymGenderSalesAPIView.as_view(), name='admin-gym-gender-sales'),

]
