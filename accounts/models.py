import secrets
import string

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from .validators import validate_iranian_phone_number
from .file_validators import validate_avatar_size


REFERRAL_ALPHABET = string.ascii_uppercase + string.digits


def generate_referral_code(length=8):
    while True:
        code = ''.join(secrets.choice(REFERRAL_ALPHABET) for _ in range(length))
        if not User.objects.filter(referral_code=code).exists():
            return code


class UserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("Phone must be set")
        extra_fields.setdefault('referral_code', generate_referral_code())
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLES_CHOICES = [
        ('customer', 'Customer'),
        ('owner', 'Owner'),
        ('admin', 'Admin'),
    ]

    phone = models.CharField(max_length=20, unique=True, validators=[validate_iranian_phone_number])
    full_name = models.CharField(max_length=250, blank=True)
    birthdate = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    role = models.CharField(max_length=20, choices=ROLES_CHOICES, default='customer')
    avatar = models.ImageField(
        upload_to='accounts/avatars/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp']), validate_avatar_size]
    )
    referral_code = models.CharField(max_length=20, unique=True, blank=True)
    referred_by = models.CharField(max_length=20, blank=True, null=True)
    is_banned_from_reviews = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = generate_referral_code()
        super().save(*args, **kwargs)

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
