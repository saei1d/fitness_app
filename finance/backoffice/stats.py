from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.utils import timezone
from django.db.models import Sum, Count, Q
from finance.models import Purchase


class MonthlyStatsAPIView(APIView):
    """API برای نمایش آمار ماهانه - باشگاه و مربی برتر"""
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request):
        now = timezone.now()
        current_month = now.month
        current_year = now.year
        
        # محاسبه باشگاه برتر ماه
        gym_stats = Purchase.objects.filter(
            payment_status='paid',
            purchase_date__month=current_month,
            purchase_date__year=current_year
        ).values(
            'package__gym__id',
            'package__gym__name'
        ).annotate(
            total_sales=Sum('final_amount'),
            total_count=Count('id')
        ).order_by('-total_sales')[:10]
        
        # محاسبه مربی برتر ماه (فعلاً خالی - بعد از اضافه شدن پکیج مربی به Purchase)
        trainer_stats = []
        
        return Response({
            'current_month': current_month,
            'current_year': current_year,
            'gym_stats': list(gym_stats),
            'trainer_stats': trainer_stats,
        })


class GymGenderSalesAPIView(APIView):
    """API برای نمایش فروش باشگاه‌ها بر اساس gender در یک ماه گذشته"""
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request):
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        one_month_ago = now - timedelta(days=30)
        
        # محاسبه فروش بر اساس gender برای هر باشگاه
        gym_gender_stats = Purchase.objects.filter(
            payment_status='paid',
            purchase_date__gte=one_month_ago
        ).values(
            'package__gym__id',
            'package__gym__name',
            'package__gender'
        ).annotate(
            total_sales=Sum('final_amount'),
            total_count=Count('id')
        ).order_by('package__gym__id', 'package__gender')
        
        # گروه‌بندی نتایج بر اساس باشگاه
        result = {}
        for stat in gym_gender_stats:
            gym_id = stat['package__gym__id']
            gym_name = stat['package__gym__name']
            gender = stat['package__gender']
            
            if gym_id not in result:
                result[gym_id] = {
                    'gym_id': gym_id,
                    'gym_name': gym_name,
                    'male_sales': 0,
                    'male_count': 0,
                    'female_sales': 0,
                    'female_count': 0,
                }
            
            if gender == 'male':
                result[gym_id]['male_sales'] += float(stat['total_sales'] or 0)
                result[gym_id]['male_count'] += stat['total_count']
            elif gender == 'female':
                result[gym_id]['female_sales'] += float(stat['total_sales'] or 0)
                result[gym_id]['female_count'] += stat['total_count']
        
        return Response({
            'period': 'last_30_days',
            'from_date': one_month_ago.isoformat(),
            'to_date': now.isoformat(),
            'gym_gender_stats': list(result.values()),
        })
