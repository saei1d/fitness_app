from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from accounts.models import User
from packages.models import Package
from discount.models import DiscountCode


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
    
    PURCHASE_TYPE_CHOICES = [
        ('gym', 'Gym Package'),
        ('trainer', 'Trainer Package'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='purchases')
    
    # Generic relation to support both Package and TrainerPackage
    purchase_type = models.CharField(max_length=10, choices=PURCHASE_TYPE_CHOICES, default='gym')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Keep package field for backward compatibility (gym packages)
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name='purchases', null=True, blank=True)
    
    buyer_code = models.CharField(max_length=100, null=True, blank=True, unique=True)
    payment_authority = models.CharField(max_length=128, null=True, blank=True, unique=True)
    payment_reference_id = models.CharField(max_length=128, null=True, blank=True)
    purchase_date = models.DateTimeField(auto_now_add=True)
    expire_date = models.DateTimeField(null=True, blank=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_purchases')
    discount_code = models.ForeignKey(DiscountCode, on_delete=models.SET_NULL, null=True, blank=True, related_name='discount_code')
    final_amount = models.DecimalField(max_digits=10, decimal_places=2)
    admin_notes = models.TextField(blank=True, null=True, help_text="توضیحات ادمین - فقط برای ادمین قابل مشاهده")
    
    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total_amount__gte=0),
                name='check_total_amount_non_negative'
            ),
            models.CheckConstraint(
                condition=models.Q(final_amount__gte=0),
                name='check_final_amount_non_negative'
            ),
            models.CheckConstraint(
                condition=models.Q(commission_amount__gte=0) | models.Q(commission_amount__isnull=True),
                name='check_commission_amount_non_negative'
            ),
            models.CheckConstraint(
                condition=models.Q(net_amount__gte=0) | models.Q(net_amount__isnull=True),
                name='check_net_amount_non_negative'
            ),
        ]

    def get_package(self):
        """Get the actual package (either gym or trainer)"""
        if self.content_object:
            return self.content_object
        if self.package:
            return self.package
        return None

    def get_package_title(self):
        pkg = self.get_package()
        return pkg.title if pkg else ''

    def get_package_price(self):
        pkg = self.get_package()
        return pkg.price if pkg else Decimal('0')

    def get_package_commission_rate(self):
        pkg = self.get_package()
        return pkg.commission_rate if pkg else 0.05

    def get_package_duration(self):
        pkg = self.get_package()
        return pkg.duration if pkg else 0

    def get_owner(self):
        """Get the owner (gym owner or trainer)"""
        pkg = self.get_package()
        if self.purchase_type == 'trainer':
            return pkg.trainer
        return pkg.gym.owner if pkg else None

    def get_owner_name(self):
        """Get owner name for display"""
        owner = self.get_owner()
        if self.purchase_type == 'trainer':
            return owner.name if owner else ''
        return owner.full_name if owner else ''

    def get_gym_or_trainer_name(self):
        """Get gym name or trainer name"""
        pkg = self.get_package()
        if self.purchase_type == 'trainer':
            return pkg.trainer.name if pkg else ''
        return pkg.gym.name if pkg else ''

    def save(self, *args, **kwargs):
        if not self.total_amount:
            pkg = self.get_package()
            if pkg:
                self.total_amount = pkg.price
        if self.commission_amount is None:
            pkg = self.get_package()
            if pkg:
                self.commission_amount = self.total_amount * Decimal(str(pkg.commission_rate))
        if self.net_amount is None:
            self.net_amount = self.total_amount - self.commission_amount
        super().save(*args, **kwargs)

    def __str__(self):
        pkg = self.get_package()
        pkg_title = pkg.title if pkg else 'Unknown'
        return f"Purchase #{self.id} - {self.user.full_name} - {pkg_title}"


class Wallet(models.Model):
    owner = models.OneToOneField(User, on_delete=models.CASCADE, limit_choices_to={'role': 'owner'})
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet for {self.owner.full_name} - Balance: {self.balance}"

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(balance__gte=0),
                name='check_wallet_balance_non_negative'
            ),
        ]


class TrainerWallet(models.Model):
    """کیف پول مربی"""
    trainer = models.OneToOneField('trainers.Trainer', on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet for {self.trainer.name} - Balance: {self.balance}"

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(balance__gte=0),
                name='check_trainer_wallet_balance_non_negative'
            ),
        ]


class AdminWallet(models.Model):
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Admin Wallet - Balance: {self.balance}"

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(balance__gte=0),
                name='check_admin_wallet_balance_non_negative'
            ),
        ]


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
    trainer_wallet = models.ForeignKey(TrainerWallet, on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
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
        if self.wallet:
            owner_name = self.wallet.owner.full_name
        elif self.trainer_wallet:
            owner_name = self.trainer_wallet.trainer.name
        elif self.admin_wallet:
            owner_name = "Admin Wallet"
        else:
            owner_name = "Unknown"
        return f"{self.type.capitalize()} - {self.amount} ({owner_name})"

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gte=0),
                name='check_transaction_amount_non_negative'
            ),
        ]


class WithdrawRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='withdraw_requests')
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='withdraw_requests')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    description = models.TextField(blank=True, help_text="توضیحات درخواست برداشت")
    admin_message = models.TextField(blank=True, help_text="پیام ادمین درباره وضعیت درخواست")
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_withdraw_requests')
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gte=0),
                name='check_withdraw_amount_non_negative'
            ),
        ]


class TrainerWithdrawRequest(models.Model):
    """درخواست برداشت مربی"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ]
    trainer = models.ForeignKey('trainers.Trainer', on_delete=models.CASCADE, related_name='withdraw_requests')
    wallet = models.ForeignKey(TrainerWallet, on_delete=models.CASCADE, related_name='withdraw_requests')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    description = models.TextField(blank=True, help_text="توضیحات درخواست برداشت")
    admin_message = models.TextField(blank=True, help_text="پیام ادمین درباره وضعیت درخواست")
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_trainer_withdraw_requests')
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gte=0),
                name='check_trainer_withdraw_amount_non_negative'
            ),
        ]
