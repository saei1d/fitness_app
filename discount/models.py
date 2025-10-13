from django.db import models
from django.utils import timezone
from django.conf import settings
from gyms.models import Gym



class DiscountCode(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percent', 'درصدی'),
        ('amount', 'مبلغ ثابت'),
    ]

    SOURCE_TYPE_CHOICES = [
        ('club', 'از سهم باشگاه'),
        ('admin', 'از سهم ادمین'),
    ]

    code = models.CharField(max_length=50, unique=True, verbose_name="کد تخفیف")
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, verbose_name="نوع تخفیف")
    value = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="مقدار تخفیف")
    
    club = models.ForeignKey(Gym, on_delete=models.CASCADE, null=True, blank=True,
                             verbose_name="باشگاه مرتبط (درصورت وجود)")
    
    source_type = models.CharField(max_length=10, choices=SOURCE_TYPE_CHOICES, verbose_name="نوع کسر تخفیف")
    
    start_date = models.DateTimeField(null=True, blank=True, verbose_name="شروع اعتبار")
    end_date = models.DateTimeField(null=True, blank=True, verbose_name="پایان اعتبار")

    usage_limit = models.PositiveIntegerField(null=True, blank=True, verbose_name="تعداد مجاز کل استفاده")
    used_count = models.PositiveIntegerField(default=0, verbose_name="تعداد استفاده‌شده")

    per_user_limit = models.PositiveIntegerField(null=True, blank=True, verbose_name="تعداد مجاز استفاده هر کاربر")

    is_active = models.BooleanField(default=True, verbose_name="فعال")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "کد تخفیف"
        verbose_name_plural = "کدهای تخفیف"
        ordering = ['-created_at']

    def __str__(self):
        return self.code


    # def is_valid(self):
    #     """بررسی اعتبار کلی کد تخفیف"""
    #     now = timezone.now()
    #     if not self.is_active:
    #         return False
    #     if self.start_date and self.start_date > now:
    #         return False
    #     if self.end_date and self.end_date < now:
    #         return False
    #     if self.usage_limit and self.used_count >= self.usage_limit:
    #         return False
    #     return True

    def can_user_use(self, user):
        """بررسی اینکه کاربر خاصی مجاز به استفاده از این کد هست یا نه"""
        # if not self.is_valid():
        #     return False
        if self.per_user_limit is None:
            return True
        user_usage_count = DiscountUsage.objects.filter(user=user, discount=self).count()
        return user_usage_count < self.per_user_limit


class DiscountUsage(models.Model):
    """ثبت استفاده کاربران از کد تخفیف"""
    discount = models.ForeignKey(DiscountCode, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('discount', 'user')
        verbose_name = "استفاده از کد تخفیف"
        verbose_name_plural = "استفاده‌های کاربران از کد تخفیف"

    def __str__(self):
        return f"{self.user} → {self.discount.code}"
