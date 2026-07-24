from django.contrib import admin
from django.urls import path
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.db.models import F
from .models import Purchase, Wallet, AdminWallet, Transaction, WithdrawRequest

User = get_user_model()


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('owner', 'balance', 'updated_at')
    readonly_fields = ('updated_at',)


@admin.register(AdminWallet)
class AdminWalletAdmin(admin.ModelAdmin):
    list_display = ('balance', 'updated_at')
    readonly_fields = ('updated_at',)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'amount', 'status', 'wallet', 'admin_wallet', 'created_at')
    list_filter = ('type', 'status', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(WithdrawRequest)
class WithdrawRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'status', 'created_at', 'processed_at')
    list_filter = ('status', 'created_at')
    readonly_fields = ('created_at', 'processed_at', 'completed_at')
    
    def save_model(self, request, obj, form, change):
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


def monthly_stats_admin_view(request):
    """Admin view برای نمایش آمار ماهانه - فراخوانی API مستقیم"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # فراخوانی مستقیم API بدون HTTP request
    from .backoffice.stats import MonthlyStatsAPIView
    
    api_view = MonthlyStatsAPIView()
    api_view.request = request
    api_view.format_kwarg = None
    
    response = api_view.get(request)
    
    return JsonResponse(response.data)


def gym_gender_sales_admin_view(request):
    """Admin view برای نمایش فروش باشگاه‌ها بر اساس gender - فراخوانی API مستقیم"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # فراخوانی مستقیم API بدون HTTP request
    from .backoffice.stats import GymGenderSalesAPIView
    
    api_view = GymGenderSalesAPIView()
    api_view.request = request
    api_view.format_kwarg = None
    
    response = api_view.get(request)
    
    return JsonResponse(response.data)


# اضافه کردن URL سفارشی به admin
admin.site.get_urls_orig = admin.site.get_urls

def get_urls():
    urls = admin.site.get_urls_orig()
    custom_urls = [
        path('monthly-stats/', admin.site.admin_view(monthly_stats_admin_view), name='monthly_stats'),
        path('gym-gender-sales/', admin.site.admin_view(gym_gender_sales_admin_view), name='gym-gender-sales'),
    ]
    return custom_urls + urls

admin.site.get_urls = get_urls
