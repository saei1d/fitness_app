from rest_framework import serializers
from .models import DiscountCode, DiscountUsage


class DiscountCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscountCode
        fields = [
            'id', 'code', 'discount_type', 'value', 'club', 'source_type',
            'start_date', 'end_date', 'usage_limit', 'used_count', 
            'per_user_limit', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'used_count', 'created_at', 'updated_at']

    def validate_code(self, value):
        """بررسی یکتایی کد تخفیف"""
        if DiscountCode.objects.filter(code=value).exists():
            raise serializers.ValidationError("این کد تخفیف قبلاً استفاده شده است.")
        return value

    def validate(self, attrs):
        """اعتبارسنجی کلی"""
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        
        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError("تاریخ شروع باید قبل از تاریخ پایان باشد.")
        
        return attrs


class DiscountUsageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscountUsage
        fields = ['id', 'discount', 'user', 'used_at']
        read_only_fields = ['id', 'user', 'used_at']
