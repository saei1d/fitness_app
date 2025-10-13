from django.contrib import admin
from .models import Purchase, Wallet, AdminWallet, Transaction


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "package", "payment_status", "verification_status", "buyer_code", "total_amount", "purchase_date", "verified_at")
    list_filter = ("payment_status", "verification_status", "purchase_date", "verified_at")
    search_fields = ("user__phone", "package__title", "buyer_code")
    readonly_fields = ("total_amount", "commission_amount", "net_amount", "buyer_code", "verified_at", "verified_by")


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "balance", "updated_at")
    search_fields = ("owner__phone",)


@admin.register(AdminWallet)
class AdminWalletAdmin(admin.ModelAdmin):
    list_display = ("id", "balance", "updated_at")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "wallet", "admin_wallet", "purchase", "amount", "type", "status", "created_at")
    list_filter = ("type", "status", "created_at")
