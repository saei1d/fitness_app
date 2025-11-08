from django.contrib import admin
from django.utils.safestring import mark_safe
from django.contrib.gis.geos import Point
from django import forms
from .models import Gym, GymImage


class GymImageInline(admin.TabularInline):
    model = GymImage
    extra = 1
    fields = ("image", "alt_text", "order")
    ordering = ("order",)


class GymAdminForm(forms.ModelForm):
    """فرم برای ورود latitude و longitude"""
    latitude_input = forms.FloatField(
        label="عرض جغرافیایی (Latitude)",
        required=True,
        help_text="مثال: 35.6892"
    )
    longitude_input = forms.FloatField(
        label="طول جغرافیایی (Longitude)",
        required=True,
        help_text="مثال: 51.3890"
    )
    
    class Meta:
        model = Gym
        exclude = ('location',)  # location را از فرم حذف می‌کنیم
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.location:
            self.fields['latitude_input'].initial = self.instance.latitude
            self.fields['longitude_input'].initial = self.instance.longitude
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        latitude = self.cleaned_data.get('latitude_input')
        longitude = self.cleaned_data.get('longitude_input')
        
        if latitude is not None and longitude is not None:
            instance.location = Point(float(longitude), float(latitude), srid=4326)
        
        if commit:
            instance.save()
        return instance


@admin.register(Gym)
class GymAdmin(admin.ModelAdmin):
    form = GymAdminForm
    list_display = ("id", "name", "owner", "address", "average_rating", "comments", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at", "average_rating")
    search_fields = ("name", "owner__phone", "address", "description")
    readonly_fields = ("created_at", "updated_at", "average_rating", "comments", "latitude_display", "longitude_display")
    filter_horizontal = ()
    inlines = [GymImageInline]
    
    fieldsets = (
        ("اطلاعات اصلی", {
            "fields": ("name", "owner", "description", "address")
        }),
        ("موقعیت جغرافیایی", {
            "fields": ("latitude_input", "longitude_input", "latitude_display", "longitude_display"),
            "description": "لطفاً مختصات جغرافیایی را وارد کنید (مثال: Latitude: 35.6892, Longitude: 51.3890)"
        }),
        ("اطلاعات اضافی", {
            "fields": ("working_hours", "banner", "average_rating", "comments")
        }),
        ("تاریخ‌ها", {
            "fields": ("created_at", "updated_at")
        }),
    )
    
    def latitude_display(self, obj):
        """نمایش عرض جغرافیایی"""
        if obj.location:
            return f"{obj.latitude:.6f}"
        return "-"
    latitude_display.short_description = "عرض جغرافیایی (خواندنی)"
    
    def longitude_display(self, obj):
        """نمایش طول جغرافیایی"""
        if obj.location:
            return f"{obj.longitude:.6f}"
        return "-"
    longitude_display.short_description = "طول جغرافیایی (خواندنی)"


@admin.register(GymImage)
class GymImageAdmin(admin.ModelAdmin):
    list_display = ("id", "gym", "image_preview", "alt_text", "order", "uploaded_at")
    list_filter = ("uploaded_at", "gym")
    search_fields = ("gym__name", "alt_text")
    readonly_fields = ("uploaded_at", "image_preview")
    ordering = ("gym", "order", "-uploaded_at")
    
    def image_preview(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" style="max-height: 50px; max-width: 50px;" />')
        return "-"
    image_preview.short_description = "پیش‌نمایش"




from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from accounts.models import User, OTP





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
