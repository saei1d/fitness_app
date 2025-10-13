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
