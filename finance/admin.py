from django.contrib import admin
from .models import Purchase, Wallet, AdminWallet, Transaction, WithdrawRequest


class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    readonly_fields = ("created_at",)
    fields = ("amount", "type", "status", "description", "created_at")
    can_delete = False


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "user_phone", "package", "payment_status", "verification_status", "buyer_code", "total_amount", "final_amount", "purchase_date", "expire_date", "verified_at")
    list_filter = ("payment_status", "verification_status", "purchase_date", "verified_at", "expire_date")
    search_fields = ("user__phone", "user__full_name", "package__title", "buyer_code")
    readonly_fields = ("total_amount", "commission_amount", "net_amount", "buyer_code", "verified_at", "verified_by", "purchase_date")
    inlines = [TransactionInline]
    
    fieldsets = (
        ("اطلاعات خرید", {
            "fields": ("user", "package", "buyer_code", "discount_code")
        }),
        ("وضعیت پرداخت", {
            "fields": ("payment_status", "verification_status", "verified_by", "verified_at")
        }),
        ("مبالغ", {
            "fields": ("total_amount", "final_amount", "commission_amount", "net_amount")
        }),
        ("تاریخ‌ها", {
            "fields": ("purchase_date", "expire_date")
        }),
    )
    
    def user_phone(self, obj):
        return obj.user.phone
    user_phone.short_description = "شماره تلفن"
    
    actions = ["mark_as_verified", "mark_as_rejected"]
    
    def mark_as_verified(self, request, queryset):
        from django.utils import timezone
        queryset.update(verification_status='verified', verified_at=timezone.now(), verified_by=request.user)
    mark_as_verified.short_description = "علامت‌گذاری به عنوان تأیید شده"
    
    def mark_as_rejected(self, request, queryset):
        queryset.update(verification_status='rejected')
    mark_as_rejected.short_description = "علامت‌گذاری به عنوان رد شده"


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "owner_phone", "balance", "transactions_count", "updated_at")
    search_fields = ("owner__phone", "owner__full_name")
    readonly_fields = ("updated_at", "transactions_count")
    inlines = [TransactionInline]
    
    fieldsets = (
        ("اطلاعات کیف پول", {
            "fields": ("owner", "balance")
        }),
        ("آمار", {
            "fields": ("transactions_count",)
        }),
        ("تاریخ", {
            "fields": ("updated_at",)
        }),
    )
    
    def owner_phone(self, obj):
        return obj.owner.phone
    owner_phone.short_description = "شماره تلفن"
    
    def transactions_count(self, obj):
        return obj.transactions.count()
    transactions_count.short_description = "تعداد تراکنش‌ها"


@admin.register(AdminWallet)
class AdminWalletAdmin(admin.ModelAdmin):
    list_display = ("id", "balance", "transactions_count", "updated_at")
    readonly_fields = ("updated_at", "transactions_count")
    inlines = [TransactionInline]
    
    fieldsets = (
        ("اطلاعات کیف پول ادمین", {
            "fields": ("balance",)
        }),
        ("آمار", {
            "fields": ("transactions_count",)
        }),
        ("تاریخ", {
            "fields": ("updated_at",)
        }),
    )
    
    def transactions_count(self, obj):
        return obj.transactions.count()
    transactions_count.short_description = "تعداد تراکنش‌ها"


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "wallet_owner", "admin_wallet_display", "purchase", "amount", "type", "status", "description_short", "created_at")
    list_filter = ("type", "status", "created_at")
    search_fields = ("wallet__owner__phone", "wallet__owner__full_name", "purchase__buyer_code", "description")
    readonly_fields = ("created_at",)
    
    fieldsets = (
        ("اطلاعات تراکنش", {
            "fields": ("wallet", "admin_wallet", "purchase", "amount", "type", "status")
        }),
        ("جزئیات", {
            "fields": ("payment_id", "description")
        }),
        ("تاریخ", {
            "fields": ("created_at",)
        }),
    )
    
    def wallet_owner(self, obj):
        if obj.wallet:
            return f"{obj.wallet.owner.full_name} ({obj.wallet.owner.phone})"
        return "-"
    wallet_owner.short_description = "مالک کیف پول"
    
    def admin_wallet_display(self, obj):
        if obj.admin_wallet:
            return "کیف پول ادمین"
        return "-"
    admin_wallet_display.short_description = "کیف پول ادمین"
    
    def description_short(self, obj):
        if obj.description:
            return obj.description[:50] + "..." if len(obj.description) > 50 else obj.description
        return "-"
    description_short.short_description = "توضیحات"


@admin.register(WithdrawRequest)
class WithdrawRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "user_phone", "wallet", "amount", "status", "processed_by", "processed_at", "completed_at")
    list_filter = ("status", "processed_at", "completed_at")
    search_fields = ("user__phone", "user__full_name", "description", "admin_message")
    readonly_fields = ("processed_at", "completed_at")
    
    fieldsets = (
        ("اطلاعات درخواست", {
            "fields": ("user", "wallet", "amount", "description")
        }),
        ("وضعیت", {
            "fields": ("status", "admin_message", "processed_by", "processed_at", "completed_at")
        }),
    )
    
    actions = ["approve_requests", "reject_requests"]
    
    def user_phone(self, obj):
        return obj.user.phone
    user_phone.short_description = "شماره تلفن"
    
    def approve_requests(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='approved', processed_by=request.user, processed_at=timezone.now())
    approve_requests.short_description = "تأیید درخواست‌های انتخاب شده"
    
    def reject_requests(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='rejected', processed_by=request.user, processed_at=timezone.now())
    reject_requests.short_description = "رد درخواست‌های انتخاب شده"
