from django.contrib import admin
from django.utils.safestring import mark_safe
from django import forms
from django.db import transaction
from .models import Gym, GymImage, GymOperator
from .services import promote_gym_owner


class GymImageInline(admin.TabularInline):
    model = GymImage
    extra = 1
    fields = ("image", "alt_text", "order")
    ordering = ("order",)


class GymAdminForm(forms.ModelForm):
    """فرم برای ورود latitude و longitude"""
    class Meta:
        model = Gym
        fields = '__all__'


@admin.register(Gym)
class GymAdmin(admin.ModelAdmin):
    form = GymAdminForm
    list_display = ("id", "name", "owner", "address", "average_rating", "order_homepage", "comments", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at", "average_rating")
    search_fields = ("name", "owner__phone", "address", "description")
    readonly_fields = ("created_at", "updated_at", "average_rating", "comments")
    filter_horizontal = ()
    inlines = [GymImageInline]
    
    fieldsets = (
        ("اطلاعات اصلی", {
            "fields": ("name", "owner", "description", "address")
        }),
        ("موقعیت جغرافیایی", {
            "fields": ("latitude", "longitude"),
            "description": "لطفاً مختصات جغرافیایی را وارد کنید (مثال: Latitude: 35.6892, Longitude: 51.3890)"
        }),
        ("اطلاعات اضافی", {
            "fields": ("working_hours", "banner", "average_rating", "comments", "order_homepage")
        }),
        ("تاریخ‌ها", {
            "fields": ("created_at", "updated_at")
        }),
    )
    

    def save_model(self, request, obj, form, change):
        with transaction.atomic():
            try:
                super().save_model(request, obj, form, change)
            except (FileNotFoundError, OSError) as e:
                # If file deletion fails due to incorrect path, continue with save
                # This happens when database has wrong path for old banner
                if 'banner' in str(e) or 'No such file' in str(e):
                    # Clear the banner field to avoid the error and retry
                    if change:
                        old_obj = Gym.objects.get(pk=obj.pk)
                        old_obj.banner = None
                        old_obj.save(update_fields=['banner'])
                        super().save_model(request, obj, form, change)
                else:
                    raise
            
            if obj.owner_id:
                promote_gym_owner(obj.owner)


@admin.register(GymImage)
class GymImageAdmin(admin.ModelAdmin):
    list_display = ("id", "gym", "image_preview", "alt_text", "order", "uploaded_at")
    list_filter = ("uploaded_at", "gym")
    search_fields = ("gym__name", "alt_text")
    readonly_fields = ("uploaded_at", "image_preview")
    ordering = ("gym", "order", "-uploaded_at")
    
    def image_preview(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" style="max-height: 50px; max-width: 50px;" />')
        return "-"
    image_preview.short_description = "پیش‌نمایش"



    # --------------------------------------------------------------


    # --------------------------------------------------------------
from finance.models import Purchase, Wallet, AdminWallet, Transaction, WithdrawRequest, TrainerWallet, TrainerWithdrawRequest


class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    readonly_fields = ("created_at",)
    fields = ("amount", "type", "status", "description", "created_at")
    can_delete = False


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "user_phone", "purchase_type", "package_display", "payment_status", "verification_status", "buyer_code", "total_amount", "final_amount", "purchase_date", "expire_date", "verified_at")
    list_filter = ("purchase_type", "payment_status", "verification_status", "purchase_date", "verified_at", "expire_date")
    search_fields = ("user__phone", "user__full_name", "content_object__title", "buyer_code")
    readonly_fields = ("total_amount", "commission_amount", "net_amount", "buyer_code", "verified_at", "verified_by", "purchase_date", "purchase_type", "content_type", "object_id")
    inlines = [TransactionInline]
    
    fieldsets = (
        ("اطلاعات خرید", {
            "fields": ("user", "purchase_type", "content_type", "object_id", "package", "buyer_code", "discount_code")
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
    
    def package_display(self, obj):
        pkg = obj.get_package()
        if pkg:
            return f"{pkg.title} ({obj.purchase_type})"
        return "-"
    package_display.short_description = "پکیج"
    
    actions = ["mark_as_verified", "mark_as_rejected"]
    
    def mark_as_verified(self, request, queryset):
        from datetime import timedelta
        from django.utils import timezone

        for purchase in queryset:
            purchase.verification_status = 'verified'
            purchase.verified_at = timezone.now()
            purchase.verified_by = request.user
            if purchase.expire_date is None:
                pkg = purchase.get_package()
                if pkg:
                    purchase.expire_date = timezone.now() + timedelta(days=purchase.get_package_duration())
            purchase.save(update_fields=['verification_status', 'verified_at', 'verified_by', 'expire_date'])
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
    
    def save_model(self, request, obj, form, change):
        from django.db import transaction
        from django.utils import timezone
        from django.db.models import F
        from finance.models import Wallet, Transaction, WithdrawRequest
        
        with transaction.atomic():
            # اگر درخواست جدید نیست و status به completed تغییر کرده است
            if change:
                try:
                    old_obj = WithdrawRequest.objects.get(pk=obj.pk)
                    if old_obj.status != 'completed' and obj.status == 'completed':
                        # بررسی موجودی کافی در کیف پول
                        if obj.wallet.balance < obj.amount:
                            raise ValueError('موجودی کیف پول کافی نیست')
                        
                        # کم کردن موجودی کیف پول
                        Wallet.objects.filter(pk=obj.wallet.pk).update(
                            balance=F('balance') - obj.amount
                        )
                        
                        # ثبت تراکنش برداشت
                        Transaction.objects.create(
                            wallet=obj.wallet,
                            amount=obj.amount,
                            type='debit',
                            status='completed',
                            description=f'برداشت درخواست #{obj.id}',
                            payment_id=None
                        )
                        
                        # تنظیم completed_at
                        obj.completed_at = timezone.now()
                        obj.processed_at = timezone.now()
                        obj.processed_by = request.user
                except WithdrawRequest.DoesNotExist:
                    pass
            
            super().save_model(request, obj, form, change)


@admin.register(TrainerWallet)
class TrainerWalletAdmin(admin.ModelAdmin):
    list_display = ("id", "trainer", "trainer_phone", "balance", "transactions_count", "updated_at")
    search_fields = ("trainer__phone", "trainer__name")
    readonly_fields = ("updated_at", "transactions_count")
    inlines = [TransactionInline]
    
    fieldsets = (
        ("اطلاعات کیف پول مربی", {
            "fields": ("trainer", "balance")
        }),
        ("آمار", {
            "fields": ("transactions_count",)
        }),
        ("تاریخ", {
            "fields": ("updated_at",)
        }),
    )
    
    def trainer_phone(self, obj):
        return obj.trainer.phone
    trainer_phone.short_description = "شماره تلفن مربی"
    
    def transactions_count(self, obj):
        return obj.transactions.count()
    transactions_count.short_description = "تعداد تراکنش‌ها"


@admin.register(TrainerWithdrawRequest)
class TrainerWithdrawRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "trainer", "trainer_phone", "wallet", "amount", "status", "processed_by", "processed_at", "completed_at")
    list_filter = ("status", "processed_at", "completed_at")
    search_fields = ("trainer__phone", "trainer__name", "description", "admin_message")
    readonly_fields = ("processed_at", "completed_at")
    
    fieldsets = (
        ("اطلاعات درخواست", {
            "fields": ("trainer", "wallet", "amount", "description")
        }),
        ("وضعیت", {
            "fields": ("status", "admin_message", "processed_by", "processed_at", "completed_at")
        }),
    )
    
    actions = ["approve_requests", "reject_requests"]
    
    def trainer_phone(self, obj):
        return obj.trainer.phone
    trainer_phone.short_description = "شماره تلفن مربی"
    
    def approve_requests(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='approved', processed_by=request.user, processed_at=timezone.now())
    approve_requests.short_description = "تأیید درخواست‌های انتخاب شده"
    
    def reject_requests(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='rejected', processed_by=request.user, processed_at=timezone.now())
    reject_requests.short_description = "رد درخواست‌های انتخاب شده"
    
    def save_model(self, request, obj, form, change):
        from django.db import transaction
        from django.utils import timezone
        from django.db.models import F
        from finance.models import TrainerWallet, Transaction, TrainerWithdrawRequest
        
        with transaction.atomic():
            if change:
                try:
                    old_obj = TrainerWithdrawRequest.objects.get(pk=obj.pk)
                    if old_obj.status != 'completed' and obj.status == 'completed':
                        if obj.wallet.balance < obj.amount:
                            raise ValueError('موجودی کیف پول کافی نیست')
                        
                        TrainerWallet.objects.filter(pk=obj.wallet.pk).update(
                            balance=F('balance') - obj.amount
                        )
                        
                        Transaction.objects.create(
                            trainer_wallet=obj.wallet,
                            amount=obj.amount,
                            type='debit',
                            status='completed',
                            description=f'برداشت مربی درخواست #{obj.id}',
                            payment_id=None
                        )
                        
                        obj.completed_at = timezone.now()
                        obj.processed_at = timezone.now()
                        obj.processed_by = request.user
                except TrainerWithdrawRequest.DoesNotExist:
                    pass
            
            super().save_model(request, obj, form, change)


@admin.register(GymOperator)
class GymOperatorAdmin(admin.ModelAdmin):
    list_display = ("id", "gym", "operator", "operator_phone", "is_active", "created_at")
    list_filter = ("is_active", "created_at", "gym")
    search_fields = ("operator__phone", "operator__full_name", "gym__name")
    readonly_fields = ("created_at",)
    
    fieldsets = (
        ("اطلاعات متصدی", {
            "fields": ("gym", "operator", "is_active")
        }),
        ("تاریخ", {
            "fields": ("created_at",)
        }),
    )
    
    def operator_phone(self, obj):
        return obj.operator.phone
    operator_phone.short_description = "شماره تلفن"
