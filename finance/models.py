from decimal import Decimal
from django.db import models
from accounts.models import User
from packages.models import Package


class Purchase(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    VERIFICATION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='purchases')
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name='purchases')
    buyer_code = models.CharField(max_length=100, null=True, blank=True)
    purchase_date = models.DateTimeField(auto_now_add=True)
    expire_date = models.DateTimeField(null=True, blank=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_purchases')

    def save(self, *args, **kwargs):

        if not self.total_amount:
            self.total_amount = self.package.price
        if not self.commission_amount:
            self.commission_amount = self.total_amount * Decimal(self.package.commission_rate)
        if not self.net_amount:
            self.net_amount = self.total_amount - self.commission_amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Purchase #{self.id} - {self.user.full_name} - {self.package.title}"


class Wallet(models.Model):
    owner = models.OneToOneField(User, on_delete=models.CASCADE, limit_choices_to={'role': 'owner'})
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet for {self.owner.full_name} - Balance: {self.balance}"


class AdminWallet(models.Model):
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Admin Wallet - Balance: {self.balance}"


class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    ]
    TRANSACTION_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    admin_wallet = models.ForeignKey(AdminWallet, on_delete=models.CASCADE, related_name='transactions', null=True,
                                     blank=True)
    purchase = models.ForeignKey(Purchase, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=6, choices=TRANSACTION_TYPES, default='credit')
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS, default='pending')
    payment_id = models.BigIntegerField(null=True, blank=True)
    description = models.TextField(blank=True, help_text="توضیحات تراکنش")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        owner_name = self.wallet.owner.full_name if self.wallet else (
            self.admin_wallet.__str__() if self.admin_wallet else "Unknown")
        return f"{self.type.capitalize()} - {self.amount} ({owner_name})"

