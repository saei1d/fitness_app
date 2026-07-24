from django.contrib import admin
from django.urls import path
from django.http import JsonResponse
from django.contrib.auth import get_user_model

User = get_user_model()


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
