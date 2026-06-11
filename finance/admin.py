from django.contrib import admin

from .models import AdminWallet, Purchase, Transaction, Wallet, WithdrawRequest


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'package', 'payment_status', 'verification_status', 'final_amount', 'purchase_date')
    list_filter = ('payment_status', 'verification_status', 'purchase_date')
    search_fields = ('user__phone', 'user__full_name', 'buyer_code', 'package__title')
    readonly_fields = ('purchase_date', 'verified_at')


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'balance', 'updated_at')
    search_fields = ('owner__phone', 'owner__full_name')
    readonly_fields = ('updated_at',)


@admin.register(AdminWallet)
class AdminWalletAdmin(admin.ModelAdmin):
    list_display = ('id', 'balance', 'updated_at')
    readonly_fields = ('updated_at',)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'wallet', 'admin_wallet', 'purchase', 'amount', 'type', 'status', 'created_at')
    list_filter = ('type', 'status', 'created_at')
    search_fields = ('purchase__buyer_code', 'wallet__owner__phone', 'description')
    readonly_fields = ('created_at',)


@admin.register(WithdrawRequest)
class WithdrawRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'wallet', 'amount', 'status', 'processed_by', 'processed_at')
    list_filter = ('status', 'processed_at', 'completed_at')
    search_fields = ('user__phone', 'user__full_name')
