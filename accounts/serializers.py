from rest_framework import serializers
from .models import User, OTP
from datetime import datetime
from django.utils import timezone


class RequestOTPSerializer(serializers.Serializer):
    phone = serializers.CharField()


class VerifyOTPSerializer(serializers.Serializer):
    phone = serializers.CharField()
    code = serializers.CharField()


class CompleteRegistrationSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    birthdate = serializers.DateField()
    password = serializers.CharField(min_length=6, write_only=True)
