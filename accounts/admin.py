from django.contrib import admin
from .models import User, OTP


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "phone", "full_name", "role", "is_staff", "is_active", "date_joined")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("phone", "full_name")
    ordering = ("-date_joined",)


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ("id", "phone", "code", "created_at", "expires_at", "is_used")
    list_filter = ("is_used", "created_at")
    search_fields = ("phone", "code")
