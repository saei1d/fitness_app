from rest_framework import serializers
from .models import Package, GroupPackage


class GroupPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupPackage
        fields = ['id', 'gym', 'title', 'description']


class PackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Package
        fields = ['id', 'group_package', 'title', 'description', 'gender', 'price', 'duration', 'commission_rate']

