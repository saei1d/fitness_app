from rest_framework import serializers
from .models import Package, GroupPackage


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
        from gyms.serializers import GymSerializer
        return GymSerializer(obj.group_package.gym, context=self.context).data

