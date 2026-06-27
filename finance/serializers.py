from decimal import Decimal
from datetime import timedelta

from django.db import transaction
from django.db.models import F

from finance.models import Purchase, Wallet, AdminWallet, Transaction, WithdrawRequest
from rest_framework import serializers
from django.utils import timezone
from discount.models import DiscountCode


class PurchaseSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_phone = serializers.CharField(source='user.phone', read_only=True)
    package_title = serializers.CharField(source='package.title', read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.full_name', read_only=True)
    # دریافت کد تخفیف به صورت رشته (اختیاری)
    discount_code = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    
    class Meta:
        model = Purchase
        fields = '__all__'
        read_only_fields = [
            'user',
            'total_amount',
            'commission_amount',
            'net_amount',
            'buyer_code',
            'payment_authority',
            'payment_reference_id',
            'verified_at',
            'verified_by',
            'final_amount',
        ]

    def validate(self, data):
        package = data.get('package')

        if not package:
            raise serializers.ValidationError("Package not found")

        # اعتبارسنجی کد تخفیف (در صورت وجود)
        discount_code_str = data.get('discount_code')
        if discount_code_str:
            code_str = discount_code_str.strip()
            discount = DiscountCode.objects.filter(code=code_str).first()
            if not discount:
                raise serializers.ValidationError({"discount_code": "کد تخفیف یافت نشد"})

            if not discount.is_valid():
                raise serializers.ValidationError({"discount_code": "کد تخفیف معتبر نیست یا ظرفیت آن تمام شده است"})

            user = self.context['request'].user
            gym = package.group_package.gym
            if discount.club and discount.club_id != gym.id:
                raise serializers.ValidationError({"discount_code": "این کد برای باشگاه انتخاب‌شده معتبر نیست"})
            if not discount.can_user_use(user):
                raise serializers.ValidationError({"discount_code": "شما مجاز به استفاده از این کد نیستید"})

            # پاس کردن آبجکت برای create
            data['discount_code_obj'] = discount

        return data

    def create(self, validated_data):
        package = validated_data['package']
        user = self.context['request'].user
        total_amount = package.price
        commission_rate = Decimal(str(package.commission_rate))

        # کمیسیون اولیه ادمین (سهم ادمین پیش از تخفیف)
        admin_commission_before_discount = total_amount * commission_rate

        # کد تخفیف (اگر معتبر بود از validate تزریق شده)
        discount_code_obj = validated_data.pop('discount_code_obj', None)
        if discount_code_obj:
            discount_code_obj = DiscountCode.objects.select_for_update().get(pk=discount_code_obj.pk)
            if not discount_code_obj.is_valid() or not discount_code_obj.can_user_use(user):
                raise serializers.ValidationError({"discount_code": "کد تخفیف دیگر قابل استفاده نیست"})

        # محاسبه مقدار تخفیف با توجه به نوع و محدودیت‌ها
        discount_amount = Decimal('0')
        if discount_code_obj:
            if discount_code_obj.discount_type == 'percent':
                requested_percent = Decimal(str(discount_code_obj.value))  # مثلا 5 یعنی 5%
                if discount_code_obj.source_type == 'admin':
                    # سقف درصد تخفیف ادمین = نرخ کمیسیون * 100
                    max_admin_percent = (commission_rate * Decimal('100')).quantize(Decimal('1.0000'))
                    effective_percent = min(requested_percent, max_admin_percent)
                else:
                    effective_percent = requested_percent
                discount_amount = (total_amount * effective_percent) / Decimal('100')
            else:  # amount
                requested_amount = Decimal(str(discount_code_obj.value))
                if discount_code_obj.source_type == 'admin':
                    # سقف مبلغی تخفیف ادمین = کل سهم کمیسیون ادمین
                    effective_amount = min(requested_amount, admin_commission_before_discount)
                else:
                    effective_amount = requested_amount
                discount_amount = effective_amount

        # محاسبه final_amount برای کاربر (نباید منفی شود)
        final_amount = total_amount - discount_amount
        if final_amount < 0:
            final_amount = Decimal('0')

        # اعمال تخفیف بر سهم‌ها بر اساس منبع تخفیف
        if discount_code_obj and discount_code_obj.source_type == 'admin':
            # تخفیف از سهم ادمین کسر می‌شود و سهم باشگاه ثابت می‌ماند.
            commission_amount = admin_commission_before_discount - min(discount_amount, admin_commission_before_discount)
            if commission_amount < 0:
                commission_amount = Decimal('0')
            net_amount = total_amount - admin_commission_before_discount
        else:
            # تخفیف باشگاه از سهم باشگاه کسر می‌شود؛ کمیسیون ادمین ثابت می‌ماند.
            commission_amount = admin_commission_before_discount
            net_amount = final_amount - commission_amount
            if net_amount < 0:
                net_amount = Decimal('0')

        purchase = Purchase.objects.create(
            user=user,
            package=package,
            discount_code=discount_code_obj,
            total_amount=total_amount,
            commission_amount=commission_amount,
            net_amount=net_amount,
            final_amount=final_amount
        )
        if discount_code_obj:
            # Atomic increment of used_count to prevent race conditions
            updated = DiscountCode.objects.filter(
                pk=discount_code_obj.pk
            ).update(used_count=F('used_count') + 1)
            
            from discount.models import DiscountUsage
            # Check for duplicate usage to prevent double-spending
            if DiscountUsage.objects.filter(discount=discount_code_obj, user=user).exists():
                # Rollback the increment if user already used this code
                DiscountCode.objects.filter(pk=discount_code_obj.pk).update(used_count=F('used_count') - 1)
                raise serializers.ValidationError({"discount_code": "شما قبلاً از این کد استفاده کرده‌اید"})
            
            DiscountUsage.objects.create(discount=discount_code_obj, user=user)
        return purchase


class WalletSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.full_name', read_only=True)
    owner_phone = serializers.CharField(source='owner.phone', read_only=True)
    transactions_count = serializers.SerializerMethodField()
    recent_transactions = serializers.SerializerMethodField()
    
    class Meta:
        model = Wallet
        fields = ['id', 'owner', 'owner_name', 'owner_phone', 'balance', 'updated_at', 'transactions_count', 'recent_transactions']
    
    def get_transactions_count(self, obj):
        """تعداد کل تراکنش‌های کیف پول"""
        return obj.transactions.count()
    
    def get_recent_transactions(self, obj):
        """آخرین 5 تراکنش کیف پول"""
        recent_transactions = obj.transactions.order_by('-created_at')[:5]
        return TransactionSerializer(recent_transactions, many=True).data


class AdminWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminWallet
        fields = '__all__'


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'


class WithdrawRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawRequest
        fields = '__all__'
        read_only_fields = ['user', 'wallet', 'status']

    def validate(self, attrs):
        request = self.context.get('request')
        if request is None:
            raise serializers.ValidationError("Request context is missing")

        user = request.user
        if not user.is_authenticated:
            raise serializers.ValidationError("Authentication required")

        if getattr(user, 'role', None) != 'owner':
            raise serializers.ValidationError("Only owners can request withdrawals")

        try:
            wallet = Wallet.objects.get(owner=user)
        except Wallet.DoesNotExist:
            raise serializers.ValidationError("Owner wallet not found")

        amount = attrs.get('amount')
        if amount is None:
            raise serializers.ValidationError({"amount": "Amount is required"})
        if amount <= 0:
            raise serializers.ValidationError({"amount": "Amount must be greater than zero"})
        if amount > wallet.balance:
            raise serializers.ValidationError({"amount": "Amount exceeds wallet balance"})

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        wallet = Wallet.objects.get(owner=user)
        withdraw_request = WithdrawRequest.objects.create(user=user, wallet=wallet, **validated_data)
        return withdraw_request


class AdminWithdrawUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawRequest
        fields = ['status', 'admin_message']

    def validate(self, attrs):
        request = self.context.get('request')
        if request is None:
            raise serializers.ValidationError("Request context is missing")

        user = request.user
        # ✅ اصلاح شرط بررسی نقش ادمین
        if not user.is_authenticated or not (user.is_staff or user.is_superuser):
            raise serializers.ValidationError("Only admin can update withdraw requests")

        new_status = attrs.get('status')
        if new_status not in ['approved', 'rejected', 'completed']:
            raise serializers.ValidationError({"status": "Invalid status transition"})

        instance = self.instance
        if instance is None:
            raise serializers.ValidationError("Instance is required")

        if instance.status == 'pending' and new_status in ['approved', 'rejected']:
            return attrs
        if instance.status == 'approved' and new_status in ['completed', 'rejected']:
            return attrs
        if instance.status in ['rejected', 'completed']:
            raise serializers.ValidationError("Withdraw request already finalized")

        raise serializers.ValidationError({"status": "Not allowed transition"})

    def update(self, instance, validated_data):
        user = self.context['request'].user
        new_status = validated_data['status']
        instance.status = new_status
        instance.admin_message = validated_data.get('admin_message', instance.admin_message)
        instance.processed_by = user
        instance.processed_at = timezone.now()
        if new_status == 'completed':
            instance.completed_at = timezone.now()
        instance.save()
        return instance


class GymMemberSerializer(serializers.Serializer):
    purchase_id = serializers.IntegerField()
    user_id = serializers.IntegerField()
    user_name = serializers.CharField()
    user_phone = serializers.CharField()
    gym_id = serializers.IntegerField()
    gym_name = serializers.CharField()
    package_id = serializers.IntegerField()
    package_title = serializers.CharField()
    payment_status = serializers.CharField()
    verification_status = serializers.CharField()
    membership_status = serializers.CharField()
    is_active = serializers.BooleanField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    final_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    purchase_date = serializers.DateTimeField()
    verified_at = serializers.DateTimeField(allow_null=True)
    expire_date = serializers.DateTimeField(allow_null=True)
    days_left = serializers.IntegerField(allow_null=True)

    def to_representation(self, instance):
        now = self.context.get('now') or timezone.now()
        purchase = instance
        gym = purchase.package.group_package.gym
        expire_date = purchase.expire_date
        is_active = (
            purchase.payment_status == 'paid'
            and purchase.verification_status == 'verified'
            and expire_date is not None
            and expire_date >= now
        )
        membership_status = 'active' if is_active else 'inactive'
        days_left = None
        if expire_date is not None:
            delta = expire_date - now
            days_left = max(int(delta.total_seconds() // 86400), 0)

        return {
            'purchase_id': purchase.id,
            'user_id': purchase.user_id,
            'user_name': purchase.user.full_name or '',
            'user_phone': purchase.user.phone,
            'gym_id': gym.id,
            'gym_name': gym.name,
            'package_id': purchase.package_id,
            'package_title': purchase.package.title,
            'payment_status': purchase.payment_status,
            'verification_status': purchase.verification_status,
            'membership_status': membership_status,
            'is_active': is_active,
            'total_amount': str(purchase.total_amount),
            'final_amount': str(purchase.final_amount),
            'purchase_date': purchase.purchase_date,
            'verified_at': purchase.verified_at,
            'expire_date': expire_date,
            'days_left': days_left,
        }


class PurchaseHistorySerializer(serializers.Serializer):
    purchase_id = serializers.IntegerField()
    buyer_code = serializers.CharField(allow_blank=True)
    user_id = serializers.IntegerField()
    user_name = serializers.CharField()
    user_phone = serializers.CharField()
    gym_id = serializers.IntegerField()
    gym_name = serializers.CharField()
    package_id = serializers.IntegerField()
    package_title = serializers.CharField()
    package_duration = serializers.IntegerField()
    payment_status = serializers.CharField()
    verification_status = serializers.CharField()
    membership_status = serializers.CharField()
    is_active = serializers.BooleanField()
    purchase_date = serializers.DateTimeField()
    start_date = serializers.DateTimeField(allow_null=True)
    end_date = serializers.DateTimeField(allow_null=True)
    verified_at = serializers.DateTimeField(allow_null=True)
    verified_by_name = serializers.CharField(allow_blank=True, allow_null=True)
    discount_code = serializers.CharField(allow_blank=True, allow_null=True)
    discount_type = serializers.CharField(allow_blank=True, allow_null=True)
    discount_value = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    discount_source_type = serializers.CharField(allow_blank=True, allow_null=True)
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = serializers.DecimalField(max_digits=6, decimal_places=2)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    commission_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    net_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    final_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    days_left = serializers.IntegerField(allow_null=True)

    def to_representation(self, instance):
        now = self.context.get('now') or timezone.now()
        purchase = instance
        gym = purchase.package.group_package.gym
        discount = purchase.discount_code

        start_date = purchase.verified_at if purchase.verification_status == 'verified' else None
        if start_date is None and purchase.payment_status == 'paid':
            start_date = purchase.purchase_date

        end_date = purchase.expire_date
        if end_date is None and start_date is not None:
            end_date = start_date + timedelta(days=purchase.package.duration)

        is_active = (
            purchase.payment_status == 'paid'
            and purchase.verification_status == 'verified'
            and end_date is not None
            and end_date >= now
        )

        if purchase.payment_status == 'failed':
            membership_status = 'failed_payment'
        elif purchase.payment_status != 'paid':
            membership_status = 'pending_payment'
        elif purchase.verification_status == 'rejected':
            membership_status = 'rejected'
        elif purchase.verification_status != 'verified':
            membership_status = 'pending_verification'
        elif is_active:
            membership_status = 'active'
        else:
            membership_status = 'expired'

        discount_amount = purchase.total_amount - purchase.final_amount
        discount_percentage = Decimal('0')
        if purchase.total_amount and purchase.total_amount > 0:
            discount_percentage = (discount_amount / purchase.total_amount) * Decimal('100')

        days_left = None
        if end_date is not None:
            days_left = max(int((end_date - now).total_seconds() // 86400), 0)

        return {
            'purchase_id': purchase.id,
            'buyer_code': purchase.buyer_code or '',
            'user_id': purchase.user_id,
            'user_name': purchase.user.full_name or '',
            'user_phone': purchase.user.phone,
            'gym_id': gym.id,
            'gym_name': gym.name,
            'package_id': purchase.package_id,
            'package_title': purchase.package.title,
            'package_duration': purchase.package.duration,
            'payment_status': purchase.payment_status,
            'verification_status': purchase.verification_status,
            'membership_status': membership_status,
            'is_active': is_active,
            'purchase_date': purchase.purchase_date,
            'start_date': start_date,
            'end_date': end_date,
            'verified_at': purchase.verified_at,
            'verified_by_name': (
                purchase.verified_by.full_name if purchase.verified_by else None
            ),
            'discount_code': discount.code if discount else None,
            'discount_type': discount.discount_type if discount else None,
            'discount_value': discount.value if discount else None,
            'discount_source_type': discount.source_type if discount else None,
            'discount_amount': discount_amount,
            'discount_percentage': discount_percentage.quantize(Decimal('1.00')),
            'total_amount': purchase.total_amount,
            'commission_amount': purchase.commission_amount or Decimal('0'),
            'net_amount': purchase.net_amount or Decimal('0'),
            'final_amount': purchase.final_amount,
            'days_left': days_left,
        }
