from accounts.imports import *
from django.db import transaction
from discount.models import DiscountCode
from rest_framework import serializers
import string
from coolname import generate

class EnterReferralCodeSerializer(serializers.Serializer):
    referral_code = serializers.CharField(max_length=20)


def generate_unique_discount_code(name, existing_codes):
    """ساخت کد تخفیف با coolname + دو رقم رندوم و یکتا."""
    base = '-'.join(generate())
    suffix = f"{random.randint(0,9)}{random.randint(0,9)}"
    code = f"{base}{suffix}"

    while code in existing_codes:
        base = generate().replace('-', '').upper()
        suffix = f"{random.randint(0,9)}{random.randint(0,9)}"
        code = f"{base}{suffix}"

    return code


# def send_sms_referral(phone, message):
#     """ارسال SMS برای کد معرف (فعلا کامنت شده چون پنل SMS نداریم)"""
#     print(f"[FAKE SMS] To: {phone}, Message: {message}")
#     # TODO: بعدا با پنل SMS واقعی جایگزین شود
#     pass


@extend_schema(tags=['Referral'])
class EnterReferralCodeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=EnterReferralCodeSerializer,
        responses={200: dict, 400: dict},
        description="وارد کردن کد معرف - کاربر باید قبلا کد معرف نداشته باشد"
    )
    @transaction.atomic
    def post(self, request):
        serializer = EnterReferralCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        referral_code = serializer.validated_data['referral_code'].strip().upper()
        current_user = request.user

        # بررسی اینکه کاربر قبلا کد معرف وارد نکرده باشد
        if current_user.referred_by:
            return Response(
                {'error': 'شما قبلا کد معرف وارد کرده‌اید.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # بررسی اینکه کاربر کد معرف خودش را وارد نکند
        if current_user.referral_code == referral_code:
            return Response(
                {'error': 'شما نمی‌توانید از کد معرف خودتان استفاده کنید.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # پیدا کردن کاربری که این کد معرف را دارد
        referrer = User.objects.filter(referral_code=referral_code).first()
        if not referrer:
            return Response(
                {'error': 'کد معرف وارد شده معتبر نیست.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ذخیره کد معرف در پروفایل کاربر فعلی
        current_user.referred_by = referral_code
        current_user.save()

        # دریافت لیست کدهای تخفیف موجود برای جلوگیری از تکراری
        existing_discount_codes = set(
            DiscountCode.objects.values_list('code', flat=True)
        )

        # ساخت کد تخفیف برای کاربر جدید (referree)
        new_user_name = current_user.full_name or current_user.phone
        new_user_discount_code = generate_unique_discount_code(
            new_user_name,
            existing_discount_codes
        )
        existing_discount_codes.add(new_user_discount_code)

        # ساخت کد تخفیف برای معرف (referrer)
        referrer_name = referrer.full_name or referrer.phone
        referrer_discount_code = generate_unique_discount_code(
            referrer_name,
            existing_discount_codes
        )

        # ایجاد کد تخفیف 5 درصد برای کاربر جدید
        discount_new_user = DiscountCode.objects.create(
            code=new_user_discount_code,
            discount_type='percent',
            value=5.00,
            club=None,
            source_type='admin',
            is_active=True
        )

        # ایجاد کد تخفیف 5 درصد برای معرف
        discount_referrer = DiscountCode.objects.create(
            code=referrer_discount_code,
            discount_type='percent',
            value=5.00,
            club=None,
            source_type='admin',
            is_active=True
        )

        # ارسال SMS به هر دو کاربر (فعلا کامنت شده)
        # message_new_user = f"کد تخفیف 5 درصد شما: {new_user_discount_code}"
        # send_sms_referral(current_user.phone, message_new_user)
        
        # message_referrer = f"به دلیل معرفی {new_user_name}، کد تخفیف 5 درصد شما: {referrer_discount_code}"
        # send_sms_referral(referrer.phone, message_referrer)
        print('hello')
        return Response({
            'success': True,
            'message': 'کد معرف با موفقیت ثبت شد.',
            'your_discount_code': new_user_discount_code,
            'discount_percent': 5,
        }, status=status.HTTP_200_OK)

