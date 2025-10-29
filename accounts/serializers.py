from rest_framework import serializers
from .models import User, OTP
from datetime import datetime
from django.utils import timezone


class RequestOTPSerializer(serializers.Serializer):
    phone = serializers.CharField()


class VerifyOTPSerializer(serializers.Serializer):
    phone = serializers.CharField()
    code = serializers.CharField()

class EditProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['full_name', 'birthdate']  


class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'phone',
            'full_name',
            'birthdate',
            'role',
            'is_staff',
            'is_superuser',
            'referral_code',
            'referred_by',
            'is_active',
            'date_joined',
        ]
        
        
class EnterReferralCodeSerializer(serializers.Serializer):
    referral_code = serializers.CharField(max_length=20)