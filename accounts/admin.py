from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, OTP

# Unregister the default User if it's already registered
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("id", "phone", "full_name", "role", "is_staff", "is_active", "is_banned_from_reviews", "date_joined")
    list_filter = ("role", "is_staff", "is_active", "is_banned_from_reviews", "date_joined")
    search_fields = ("phone", "full_name", "referral_code")
    ordering = ("-date_joined",)
    readonly_fields = ("date_joined", "last_login")
    
    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("اطلاعات شخصی", {"fields": ("full_name", "birthdate", "role", "referral_code", "referred_by")}),
        ("دسترسی‌ها", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("تنظیمات", {"fields": ("is_banned_from_reviews",)}),
        ("تاریخ‌ها", {"fields": ("last_login", "date_joined")}),
    )
    
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone", "password1", "password2", "full_name", "role", "is_staff", "is_active"),
        }),
    )
    
    filter_horizontal = ("groups", "user_permissions")


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ("id", "phone", "code", "created_at", "expires_at", "is_used", "is_expired_display")
    list_filter = ("is_used", "created_at")
    search_fields = ("phone", "code")
    readonly_fields = ("created_at", "is_expired_display")
    ordering = ("-created_at",)
    
    def is_expired_display(self, obj):
        return obj.is_expired()
    is_expired_display.short_description = "منقضی شده"
    is_expired_display.boolean = True
