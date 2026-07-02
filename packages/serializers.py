from rest_framework import serializers
from .models import Package, GroupPackage
from gyms.models import Gym


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

    class Meta:
        model = Package
        fields = ['id', 'group_package', 'title', 'description', 'gender', 'price', 'duration', 'commission_rate','sessions', 'gym']

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

