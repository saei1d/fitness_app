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
        extra_kwargs = {
            'code': {
                'help_text': 'کد تخفیف یکتا (مثال: SUMMER2024)'
            },
            'discount_type': {
                'help_text': 'نوع تخفیف: percent (درصدی) یا amount (مبلغ ثابت)'
            },
            'value': {
                'help_text': 'مقدار تخفیف (برای درصد: 0-100، برای مبلغ: مقدار به ریال)'
            },
            'club': {
                'help_text': 'باشگاه مرتبط (برای source_type=club الزامی، برای admin=null)'
            },
            'source_type': {
                'help_text': 'منبع کسر تخفیف: club (از سهم باشگاه) یا admin (از سهم ادمین)'
            },
            'start_date': {
                'help_text': 'تاریخ شروع اعتبار (اختیاری)'
            },
            'end_date': {
                'help_text': 'تاریخ پایان اعتبار (اختیاری)'
            },
            'usage_limit': {
                'help_text': 'تعداد مجاز کل استفاده (اختیاری)'
            },
            'per_user_limit': {
                'help_text': 'تعداد مجاز استفاده هر کاربر (اختیاری)'
            },
            'is_active': {
                'help_text': 'وضعیت فعال بودن کد تخفیف'
            }
        }

    def validate_code(self, value):
        """بررسی یکتایی کد تخفیف، با استثناء رکورد در حال ویرایش"""
        qs = DiscountCode.objects.filter(code=value)
        instance = getattr(self, 'instance', None)
        if instance is not None:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError("این کد تخفیف قبلاً استفاده شده است.")
        return value

    def validate(self, attrs):
        """اعتبارسنجی کلی + قواعد دسترسی ساخت/ویرایش"""
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')

        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError("تاریخ شروع باید قبل از تاریخ پایان باشد.")

        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return attrs

        user = request.user

        # Determine effective values (for update may be missing from attrs)
        source_type = attrs.get('source_type')
        club = attrs.get('club')

        if self.instance is not None:
            # On update, fallback to existing values
            if source_type is None:
                source_type = self.instance.source_type
            if club is None:
                club = self.instance.club

        # Owners constraints
        if not user.is_staff and getattr(user, 'role', None) == 'owner':
            # Owner can only work with their own club
            if club is None:
                raise serializers.ValidationError("مالک باشگاه باید برای باشگاه خود کد بسازد.")
            if getattr(club, 'owner', None) != user:
                raise serializers.ValidationError("شما فقط می‌توانید برای باشگاه خودتان کد تخفیف بسازید/ویرایش کنید.")

            # Owner can only use club source
            if source_type != 'club':
                raise serializers.ValidationError("مالک باشگاه فقط می‌تواند کد با منبع 'club' ایجاد/ویرایش کند.")

        # If source_type is admin, club must be null (by business rule); if club, club required
        if source_type == 'admin' and club is not None:
            raise serializers.ValidationError("برای کدهای منبع ادمین نباید باشگاهی انتخاب شود.")
        if source_type == 'club' and club is None:
            raise serializers.ValidationError("برای کدهای منبع باشگاه انتخاب باشگاه الزامی است.")

        return attrs


class DiscountUsageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscountUsage
        fields = ['id', 'discount', 'user', 'used_at']
        read_only_fields = ['id', 'user', 'used_at']
        extra_kwargs = {
            'discount': {
                'help_text': 'کد تخفیف استفاده شده'
            },
            'user': {
                'help_text': 'کاربری که از کد استفاده کرده'
            },
            'used_at': {
                'help_text': 'زمان استفاده از کد تخفیف'
            }
        }
