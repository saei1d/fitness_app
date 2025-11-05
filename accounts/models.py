from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("Phone must be set")
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)  # تنظیم رمز عبور
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    phone = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=250, blank=True)
    birthdate = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    ROLES_CHOICES = [
        ('customer', 'Customer'),
        ('owner', 'Owner'),
        ('admin', 'Admin'),
    ]
    role = models.CharField(max_length=20, choices=ROLES_CHOICES, default='customer')
    referral_code = models.CharField(max_length=20)
    referred_by = models.CharField(max_length=20, blank=True , null=True)
    is_banned_from_reviews = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.phone


class OTP(models.Model):
    phone = models.CharField(max_length=20)
    code = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.phone} - {self.code}"
