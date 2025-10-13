from decimal import Decimal

from finance.models import Purchase, Wallet, AdminWallet, Transaction
from rest_framework import serializers


class PurchaseSerializer(serializers.ModelSerializer):
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
    class Meta:
        model = Wallet
        fields = '__all__'


class AdminWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminWallet
        fields = '__all__'


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'
