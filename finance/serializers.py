from decimal import Decimal

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
        read_only_fields = ['user', 'total_amount', 'commission_amount', 'net_amount', 'buyer_code', 'verified_at', 'verified_by', 'final_amount']

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

            if not discount.is_active:
                raise serializers.ValidationError({"discount_code": "کد تخفیف غیرفعال است"})

            now = timezone.now()
            if discount.start_date and discount.start_date > now:
                raise serializers.ValidationError({"discount_code": "کد تخفیف هنوز فعال نشده"})
            if discount.end_date and discount.end_date < now:
                raise serializers.ValidationError({"discount_code": "کد تخفیف منقضی شده"})

            if discount.usage_limit and discount.used_count >= discount.usage_limit:
                raise serializers.ValidationError({"discount_code": "حداکثر تعداد استفاده از این کد تمام شده"})

            user = self.context['request'].user
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
            # تخفیف از سهم ادمین کسر می‌شود تا سقف سهم ادمین
            commission_amount = admin_commission_before_discount - min(discount_amount, admin_commission_before_discount)
            if commission_amount < 0:
                commission_amount = Decimal('0')
            net_amount = total_amount - commission_amount
        else:
            # تخفیف باشگاه از سهم باشگاه کسر می‌شود؛ کمیسیون ادمین ثابت می‌ماند
            commission_amount = admin_commission_before_discount
            net_amount = total_amount - commission_amount - discount_amount
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
