from decimal import Decimal
from datetime import timedelta

from django.db import transaction
from django.db.models import F, Q
from django.contrib.contenttypes.models import ContentType

from accounts.permissions import is_platform_admin
from accounts.serializers import CardNumberField
from finance.models import Purchase, Wallet, AdminWallet, Transaction, WithdrawRequest, TrainerWallet, TrainerWithdrawRequest
from finance.pricing import split_purchase_amounts
from rest_framework import serializers
from django.utils import timezone
from discount.models import DiscountCode, PackageDiscount
from trainers.models import TrainerPackage


class PurchaseSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_phone = serializers.CharField(source='user.phone', read_only=True)
    package_title = serializers.SerializerMethodField()
    verified_by_name = serializers.CharField(source='verified_by.full_name', read_only=True)
    # دریافت کد تخفیف به صورت رشته (اختیاری)
    discount_code = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    admin_notes = serializers.CharField(read_only=True, required=False, allow_null=True)
    code_expire_date = serializers.SerializerMethodField(read_only=True)
    is_code_expired = serializers.SerializerMethodField(read_only=True)
    purchase_type = serializers.CharField(read_only=True)
    owner_name = serializers.SerializerMethodField()
    gym_or_trainer_name = serializers.SerializerMethodField()
    # Field for trainer package booking
    trainer_package = serializers.PrimaryKeyRelatedField(
        queryset=TrainerPackage.objects.all(),
        write_only=True,
        required=False,
        allow_null=True
    )

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
            'purchase_type',
            'content_type',
            'object_id',
        ]

    def get_package_title(self, instance):
        pkg = instance.get_package()
        return pkg.title if pkg else ''

    def get_owner_name(self, instance):
        return instance.get_owner_name()

    def get_gym_or_trainer_name(self, instance):
        return instance.get_gym_or_trainer_name()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        # فقط ادمین می‌تواند admin_notes را ببیند
        if request and not is_platform_admin(request.user):
            data.pop('admin_notes', None)
        return data

    def get_code_expire_date(self, instance):
        if instance.purchase_date:
            return (instance.purchase_date + timedelta(days=7)).strftime('%Y-%m-%d %H:%M')
        return None

    def get_is_code_expired(self, instance):
        if instance.purchase_date:
            return timezone.now() > instance.purchase_date + timedelta(days=7)
        return False

    def validate(self, data):
        # Validate package (either gym or trainer)
        package = data.get('package')
        trainer_package = data.get('trainer_package')
        
        if not package and not trainer_package:
            raise serializers.ValidationError("Package or TrainerPackage is required")

        # Validate discount code (if provided)
        discount_code_str = data.get('discount_code')
        if discount_code_str:
            code_str = discount_code_str.strip()
            discount = DiscountCode.objects.filter(code=code_str).prefetch_related('packages').first()
            if not discount:
                raise serializers.ValidationError({"discount_code": "کد تخفیف یافت نشد"})

            if not discount.is_valid():
                raise serializers.ValidationError({"discount_code": "کد تخفیف معتبر نیست یا ظرفیت آن تمام شده است"})

            user = self.context['request'].user

            # کد مخصوص یک باشگاه نباید روی پکیج مربی بنشیند.
            # کد سراسری ادمین، مثل کد معرفی، همچنان برای مربی معتبر است.
            if trainer_package and (
                discount.gym_id
                or discount.source_type != 'admin'
                or discount.packages.exists()
            ):
                raise serializers.ValidationError({"discount_code": "این کد برای پکیج مربی معتبر نیست"})

            # For gym packages, check gym match
            if package and not trainer_package:
                gym = package.gym
                if discount.gym and discount.gym_id != gym.id:
                    raise serializers.ValidationError({"discount_code": "این کد برای باشگاه انتخاب‌شده معتبر نیست"})
                
                # If packages are selected, check if this package is in them
                if discount.packages.exists():
                    if package not in discount.packages.all():
                        raise serializers.ValidationError({"discount_code": "این کد برای پکیج انتخاب‌شده معتبر نیست"})
            
            if not discount.can_user_use(user):
                raise serializers.ValidationError({"discount_code": "شما مجاز به استفاده از این کد نیستید"})

            # Pass object for create
            data['discount_code_obj'] = discount

        return data

    def create(self, validated_data):
        package = validated_data.get('package')
        trainer_package = validated_data.get('trainer_package')
        user = self.context['request'].user
        
        # Determine package type and get common fields
        if trainer_package:
            purchase_type = 'trainer'
            pkg = trainer_package
            content_type = ContentType.objects.get_for_model(trainer_package.__class__)
            object_id = trainer_package.pk
        else:
            purchase_type = 'gym'
            pkg = package
            content_type = ContentType.objects.get_for_model(package.__class__)
            object_id = package.pk
        
        total_amount = pkg.price
        commission_rate = Decimal(str(pkg.commission_rate))

        # Initial admin commission (before discount)
        admin_commission_before_discount = total_amount * commission_rate

        # Discount code (if valid, injected from validate)
        discount_code_obj = validated_data.pop('discount_code_obj', None)
        if discount_code_obj:
            discount_code_obj = DiscountCode.objects.select_for_update().get(pk=discount_code_obj.pk)
            if not discount_code_obj.is_valid() or not discount_code_obj.can_user_use(user):
                raise serializers.ValidationError({"discount_code": "کد تخفیف دیگر قابل استفاده نیست"})

        # Check package discount
        package_discount_obj = None
        from django.utils import timezone
        now = timezone.now()
        
        # Only gym packages have PackageDiscount
        if purchase_type == 'gym':
            package_discount_obj = pkg.discounts.filter(
                is_active=True,
            ).filter(
                Q(start_date__isnull=True) | Q(start_date__lte=now),
                Q(end_date__isnull=True) | Q(end_date__gte=now),
            ).first()

        # Calculate discount amount with limits
        discount_details = []

        # Calculate package discount (if exists)
        package_discount_amount = Decimal('0')
        if package_discount_obj:
            if package_discount_obj.discount_type == 'percent':
                requested_percent = Decimal(str(package_discount_obj.value))
                # For backward compatibility: if value < 1, convert to percent
                if requested_percent < Decimal('1'):
                    requested_percent = requested_percent * Decimal('100')
                if package_discount_obj.source_type == 'admin':
                    max_admin_percent = (commission_rate * Decimal('100')).quantize(Decimal('1.0000'))
                    effective_percent = min(requested_percent, max_admin_percent)
                else:
                    effective_percent = requested_percent
                package_discount_amount = (total_amount * effective_percent) / Decimal('100')
                discount_details.append(f"تخفیف پکیج: ({effective_percent}% از {package_discount_obj.source_type})")
            else:  # amount
                requested_amount = Decimal(str(package_discount_obj.value))
                if package_discount_obj.source_type == 'admin':
                    effective_amount = min(requested_amount, admin_commission_before_discount)
                else:
                    effective_amount = requested_amount
                package_discount_amount = effective_amount
                discount_details.append(f"تخفیف پکیج: ({effective_amount} تومان از {package_discount_obj.source_type})")

        # Calculate code discount (on price after package discount)
        code_discount_amount = Decimal('0')
        if discount_code_obj:
            price_after_package_discount = total_amount - package_discount_amount
            if price_after_package_discount < 0:
                price_after_package_discount = Decimal('0')
            if discount_code_obj.discount_type == 'percent':
                requested_percent = Decimal(str(discount_code_obj.value))
                # For backward compatibility: if value < 1, convert to percent
                if requested_percent < Decimal('1'):
                    requested_percent = requested_percent * Decimal('100')
                if discount_code_obj.source_type == 'admin':
                    max_admin_percent = (commission_rate * Decimal('100')).quantize(Decimal('1.0000'))
                    effective_percent = min(requested_percent, max_admin_percent)
                else:
                    effective_percent = requested_percent
                code_discount_amount = (price_after_package_discount * effective_percent) / Decimal('100')
                discount_details.append(f"کد تخفیف: {discount_code_obj.code} ({effective_percent}% از {discount_code_obj.source_type})")
            else:  # amount
                requested_amount = Decimal(str(discount_code_obj.value))
                if discount_code_obj.source_type == 'admin':
                    effective_amount = min(requested_amount, admin_commission_before_discount)
                else:
                    effective_amount = requested_amount
                code_discount_amount = effective_amount
                discount_details.append(f"کد تخفیف: {discount_code_obj.code} ({effective_amount} تومان از {discount_code_obj.source_type})")

        # سهم‌ها جدا سقف می‌خورند. خرید بدون تخفیف همان قیمت و کمیسیون قبلی را نگه می‌دارد.
        package_source = package_discount_obj.source_type if package_discount_obj else None
        code_source = discount_code_obj.source_type if discount_code_obj else None
        commission_amount, net_amount, final_amount, _, _ = split_purchase_amounts(
            total_amount=total_amount,
            admin_commission=admin_commission_before_discount,
            package_discount_amount=package_discount_amount,
            package_source=package_source,
            code_discount_amount=code_discount_amount,
            code_source=code_source,
        )

        # Build admin notes
        admin_notes = f"قیمت اصلی: {total_amount} تومان\n"
        if discount_details:
            admin_notes += "\n".join(discount_details) + "\n"
        admin_notes += f"قیمت نهایی: {final_amount} تومان\n"
        admin_notes += f"کمیسیون ادمین: {commission_amount} تومان\n"
        admin_notes += f"سهم {'مربی' if purchase_type == 'trainer' else 'باشگاه'}: {net_amount} تومان"

        purchase = Purchase.objects.create(
            user=user,
            purchase_type=purchase_type,
            content_type=content_type,
            object_id=object_id,
            package=package,  # Keep for backward compatibility
            discount_code=discount_code_obj,
            total_amount=total_amount,
            commission_amount=commission_amount,
            net_amount=net_amount,
            final_amount=final_amount,
            admin_notes=admin_notes
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


class TrainerWalletSerializer(serializers.ModelSerializer):
    """سریالایزر کیف پول مربی"""
    trainer_name = serializers.CharField(source='trainer.name', read_only=True)
    trainer_phone = serializers.CharField(source='trainer.user.phone', read_only=True)
    transactions_count = serializers.SerializerMethodField()
    recent_transactions = serializers.SerializerMethodField()
    
    class Meta:
        model = TrainerWallet
        fields = ['id', 'trainer', 'trainer_name', 'trainer_phone', 'balance', 'updated_at', 'transactions_count', 'recent_transactions']
    
    def get_transactions_count(self, obj):
        return obj.transactions.count()
    
    def get_recent_transactions(self, obj):
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
    card_number = CardNumberField(write_only=True, required=False)

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

        if not attrs.get('card_number') and not user.card_number:
            raise serializers.ValidationError({
                "card_number": "برای ثبت درخواست برداشت، ابتدا شماره کارت خود را در پروفایل ثبت کنید."
            })

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        card_number = validated_data.pop('card_number', None)
        if card_number and card_number != user.card_number:
            user.card_number = card_number
            user.save(update_fields=['card_number'])

        wallet = Wallet.objects.get(owner=user)
        withdraw_request = WithdrawRequest.objects.create(user=user, wallet=wallet, **validated_data)
        return withdraw_request


class TrainerWithdrawRequestSerializer(serializers.ModelSerializer):
    card_number = CardNumberField(write_only=True, required=False)

    class Meta:
        model = TrainerWithdrawRequest
        fields = '__all__'
        read_only_fields = ['trainer', 'wallet', 'status']

    def validate(self, attrs):
        request = self.context.get('request')
        if request is None:
            raise serializers.ValidationError("Request context is missing")

        user = request.user
        if not user.is_authenticated:
            raise serializers.ValidationError("Authentication required")

        if getattr(user, 'role', None) != 'trainer':
            raise serializers.ValidationError("Only trainers can request withdrawals")

        trainer = self.context.get('trainer')
        wallet = self.context.get('wallet')

        if trainer is None:
            raise serializers.ValidationError("Trainer context is missing")
        if wallet is None:
            raise serializers.ValidationError("Wallet context is missing")

        amount = attrs.get('amount')
        if amount is None:
            raise serializers.ValidationError({"amount": "Amount is required"})
        if amount <= 0:
            raise serializers.ValidationError({"amount": "Amount must be greater than zero"})
        if amount > wallet.balance:
            raise serializers.ValidationError({"amount": "Amount exceeds wallet balance"})

        if not attrs.get('card_number') and not user.card_number:
            raise serializers.ValidationError({
                "card_number": "برای ثبت درخواست برداشت، ابتدا شماره کارت خود را در پروفایل ثبت کنید."
            })

        return attrs

    def create(self, validated_data):
        trainer = self.context['trainer']
        user = self.context['request'].user

        card_number = validated_data.pop('card_number', None)
        if card_number and card_number != user.card_number:
            user.card_number = card_number
            user.save(update_fields=['card_number'])

        wallet = self.context['wallet']
        withdraw_request = TrainerWithdrawRequest.objects.create(trainer=trainer, wallet=wallet, **validated_data)
        return withdraw_request


class AdminWithdrawRequestReadSerializer(serializers.ModelSerializer):
    """Read-only serializer for admin lists/details, includes user's card number."""
    card_number = serializers.CharField(source='user.card_number', read_only=True)

    class Meta:
        model = WithdrawRequest
        fields = '__all__'


class AdminTrainerWithdrawRequestReadSerializer(serializers.ModelSerializer):
    """Read-only serializer for admin lists/details, includes trainer's card number."""
    card_number = serializers.SerializerMethodField()

    class Meta:
        model = TrainerWithdrawRequest
        fields = '__all__'

    def get_card_number(self, obj):
        user = obj.trainer.user if obj.trainer_id else None
        return user.card_number if user else None


class AdminWithdrawUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawRequest
        fields = ['status', 'admin_message']

    def validate(self, attrs):
        request = self.context.get('request')
        if request is None:
            raise serializers.ValidationError("Request context is missing")

        if not is_platform_admin(request.user):
            raise serializers.ValidationError("Only admin can update withdraw requests")

        new_status = attrs.get('status')
        if new_status not in ['pending', 'approved', 'rejected', 'completed']:
            raise serializers.ValidationError({"status": "Invalid status"})

        return attrs


class AdminTrainerWithdrawUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainerWithdrawRequest
        fields = ['status', 'admin_message']

    def validate(self, attrs):
        request = self.context.get('request')
        if request is None:
            raise serializers.ValidationError("Request context is missing")

        if not is_platform_admin(request.user):
            raise serializers.ValidationError("Only admin can update trainer withdraw requests")

        new_status = attrs.get('status')
        if new_status not in ['pending', 'approved', 'rejected', 'completed']:
            raise serializers.ValidationError({"status": "Invalid status"})

        return attrs

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
    purchase_type = serializers.CharField()
    gym_id = serializers.IntegerField(allow_null=True)
    gym_name = serializers.CharField(allow_blank=True)
    trainer_id = serializers.IntegerField(allow_null=True)
    trainer_name = serializers.CharField(allow_blank=True)
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
        pkg = purchase.get_package()
        
        gym_id = None
        gym_name = ''
        trainer_id = None
        trainer_name = ''
        
        if purchase.purchase_type == 'trainer':
            trainer_id = pkg.trainer_id if pkg else None
            trainer_name = pkg.trainer.name if pkg and hasattr(pkg, 'trainer') else ''
        else:
            gym_id = pkg.gym_id if pkg else None
            gym_name = pkg.gym.name if pkg and hasattr(pkg, 'gym') else ''
        
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
            'purchase_type': purchase.purchase_type,
            'gym_id': gym_id,
            'gym_name': gym_name,
            'trainer_id': trainer_id,
            'trainer_name': trainer_name,
            'package_id': purchase.object_id,
            'package_title': purchase.get_package_title(),
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
    purchase_type = serializers.CharField()
    gym_id = serializers.IntegerField(allow_null=True)
    gym_name = serializers.CharField(allow_blank=True)
    trainer_id = serializers.IntegerField(allow_null=True)
    trainer_name = serializers.CharField(allow_blank=True)
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
        pkg = purchase.get_package()
        discount = purchase.discount_code

        gym_id = None
        gym_name = ''
        trainer_id = None
        trainer_name = ''
        
        if purchase.purchase_type == 'trainer':
            trainer_id = pkg.trainer_id if pkg else None
            trainer_name = pkg.trainer.name if pkg and hasattr(pkg, 'trainer') else ''
        else:
            gym_id = pkg.gym_id if pkg else None
            gym_name = pkg.gym.name if pkg and hasattr(pkg, 'gym') else ''

        start_date = purchase.verified_at if purchase.verification_status == 'verified' else None
        if start_date is None and purchase.payment_status == 'paid':
            start_date = purchase.purchase_date

        end_date = purchase.expire_date
        if end_date is None and start_date is not None:
            end_date = start_date + timedelta(days=purchase.get_package_duration())

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
            'purchase_type': purchase.purchase_type,
            'gym_id': gym_id,
            'gym_name': gym_name,
            'trainer_id': trainer_id,
            'trainer_name': trainer_name,
            'package_id': purchase.object_id,
            'package_title': purchase.get_package_title(),
            'package_duration': purchase.get_package_duration(),
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
