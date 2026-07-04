from rest_framework import serializers
from .models import Package, GroupPackage
from gyms.models import Gym
from discount.models import PackageDiscount


class GymSimpleSerializer(serializers.ModelSerializer):
    """سریالایزر ساده باشگاه برای جلوگیری از حلقه بی‌نهایت"""
    class Meta:
        model = Gym
        fields = ['id', 'name', 'description', 'address', 'banner', 'average_rating']


class GroupPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupPackage
        fields = ['id', 'gym', 'title', 'description']


class PackageSerializer(serializers.ModelSerializer):
    gym = serializers.SerializerMethodField()
    discount = serializers.SerializerMethodField()

    class Meta:
        model = Package
        fields = ['id', 'group_package', 'title', 'description', 'gender', 'price', 'duration', 'commission_rate','sessions', 'gym', 'discount']

    def get_gym(self, obj):
        request = self.context.get('request')
        gym_data = GymSimpleSerializer(obj.group_package.gym).data
        if obj.group_package.gym.banner and hasattr(obj.group_package.gym.banner, 'url'):
            url = obj.group_package.gym.banner.url
            if request:
                url = request.build_absolute_uri(url)
            gym_data['banner'] = url
        else:
            gym_data['banner'] = None
        return gym_data

    def get_discount(self, obj):
        """بررسی و بازگرداندن تخفیف فعال روی پکیج"""
        from django.utils import timezone
        from django.db.models import Q
        now = timezone.now()
        active_discount = obj.discounts.filter(
            Q(is_active=True) &
            (Q(start_date__lte=now) | Q(start_date__isnull=True)) &
            (Q(end_date__gte=now) | Q(end_date__isnull=True))
        ).first()
        if active_discount:
            return {
                'id': active_discount.id,
                'discount_type': active_discount.discount_type,
                'value': str(active_discount.value),
                'source_type': active_discount.source_type
            }
        return None

