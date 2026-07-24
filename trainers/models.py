from django.db import models
from django.core.validators import FileExtensionValidator
from gyms.models import Gym
import os


def trainer_image_upload_path(instance, filename):
    trainer_id = str(instance.id) if instance.id else 'temp'
    return os.path.join("trainers", "images", trainer_id, filename)


class Trainer(models.Model):
    """مدل مربی"""
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    image = models.ImageField(
        upload_to=trainer_image_upload_path,
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])]
    )
    
    # تخصص‌ها
    specializations = models.JSONField(
        default=list,
        help_text="لیست تخصص‌ها مثل: ['بدنسازی', 'کراسفیت', 'TRX']"
    )
    teaching_experience_years = models.PositiveIntegerField(
        default=0,
        help_text="سابقه تدریس به سال"
    )
    certifications = models.JSONField(
        default=list,
        help_text="لیست مدارک و گواهینامه‌ها مثل: ['مربیگری درجه ۱', 'مربیگری درجه ۲']"
    )
    special_expertise = models.JSONField(
        default=list,
        help_text="تخصص‌های ویژه مثل: ['کاهش وزن', 'حجم', 'توانبخشی']"
    )
    
    # باشگاه‌های فعال
    active_gyms = models.ManyToManyField(
        Gym,
        blank=True,
        related_name='active_trainers',
        help_text="باشگاه‌هایی که در آن‌ها فعال است"
    )
    
    # آمار
    active_students_count = models.PositiveIntegerField(
        default=0,
        help_text="تعداد شاگردان فعال"
    )
    
    # بیوگرافی کوتاه
    bio = models.CharField(
        max_length=255,
        blank=True,
        help_text="تیتر کوتاه زیر اسم مربی"
    )
    
    # امتیاز و نظرات
    average_rating = models.FloatField(default=0.0)
    reviews_count = models.IntegerField(default=0)
    
    # ترتیب نمایش در صفحه اصلی
    order_homepage = models.IntegerField(
        default=0,
        help_text="Order for homepage display (0 = use default sorting)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Trainer"
        verbose_name_plural = "Trainers"
    
    def __str__(self):
        return f"{self.name} ({self.phone})"
    
    def update_rating(self):
        """به‌روزرسانی امتیاز میانگین"""
        reviews = self.reviews.filter(deleted=False, blocked=False)
        if reviews.exists():
            self.average_rating = sum(review.rating for review in reviews) / reviews.count()
            self.reviews_count = reviews.count()
        else:
            self.average_rating = 0.0
            self.reviews_count = 0
        self.save(update_fields=['average_rating', 'reviews_count'])


class TrainerGroupPackage(models.Model):
    """گروه پکیج مربی (مشابه GroupPackage برای باشگاه)"""
    trainer = models.ForeignKey(Trainer, on_delete=models.CASCADE, related_name="group_packages")
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.title} - {self.trainer.name}"


class TrainerPackage(models.Model):
    """پکیج مربی (مشابه Package برای باشگاه)"""
    group_package = models.ForeignKey(
        TrainerGroupPackage,
        on_delete=models.CASCADE,
        related_name="packages"
    )
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    gender = models.CharField(
        max_length=100,
        choices=[('male', 'Male'), ('female', 'Female')]
    )
    price = models.DecimalField(max_digits=15, decimal_places=2)
    duration = models.IntegerField(help_text="Duration in days")
    commission_rate = models.FloatField(
        help_text="Commission rate 0.05 is 5 percent",
        default=0.05
    )
    sessions = models.IntegerField(
        default=0,
        help_text="Number of sessions"
    )
    order_homepage = models.IntegerField(
        default=0,
        help_text="Order for homepage display (0 = use default sorting)"
    )
    
    def __str__(self):
        gender_display = self.get_gender_display()
        short_desc = (self.description[:50] + '...') if len(self.description) > 50 else self.description
        trainer_name = self.group_package.trainer.name
        return f"{self.title} ({gender_display}) - {trainer_name} - {short_desc}"


class TrainerReview(models.Model):
    """نظرات شاگردان برای مربی"""
    trainer = models.ForeignKey(
        Trainer,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='trainer_reviews'
    )
    rating = models.PositiveSmallIntegerField(
        choices=[(i, str(i)) for i in range(1, 6)]
    )
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_reported = models.BooleanField(default=False)
    buyer = models.BooleanField(default=False, help_text="آیا از این مربی خرید داشته")
    blocked = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )
    
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Trainer Review"
        verbose_name_plural = "Trainer Reviews"
    
    def __str__(self):
        return f"Review by {self.user.phone} for {self.trainer.name}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.trainer.update_rating()
