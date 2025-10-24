from decimal import Decimal

from finance.models import Purchase, Wallet, AdminWallet, Transaction, WithdrawRequest
from rest_framework import serializers
from django.utils import timezone


class PurchaseSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_phone = serializers.CharField(source='user.phone', read_only=True)
    package_title = serializers.CharField(source='package.title', read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.full_name', read_only=True)
    
    class Meta:
        model = Purchase
        fields = '__all__'
        read_only_fields = ['user', 'total_amount', 'commission_amount', 'net_amount', 'buyer_code', 'verified_at', 'verified_by']

    def validate(self, data):
        package = data.get('package')

        if not package:
            raise serializers.ValidationError("Package not found")

        return data

    def create(self, validated_data):
        package = validated_data['package']
        user = self.context['request'].user
        total_amount = package.price
        commission_rate = Decimal(str(package.commission_rate))
        commission_amount = total_amount * commission_rate
        net_amount = total_amount - commission_amount

        # ایجاد Purchase
        purchase = Purchase.objects.create(
            user=user,
            package=package,
            total_amount=total_amount,
            commission_amount=commission_amount,
            net_amount=net_amount
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
        if not user.is_authenticated or getattr(user, 'role', None) != 'admin':
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