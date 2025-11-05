from django.contrib import admin
from .models import DiscountCode, DiscountUsage
from django.utils import timezone


class DiscountUsageInline(admin.TabularInline):
    model = DiscountUsage
    extra = 0
    readonly_fields = ("used_at",)
    can_delete = False


@admin.register(DiscountCode)
class DiscountCodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'discount_type', 'value', 'club', 'source_type', 'is_active', 'is_valid_display', 'used_count', 'usage_limit', 'created_at')
    list_filter = ('discount_type', 'source_type', 'is_active', 'created_at')
    search_fields = ('code', 'club__name')
    readonly_fields = ('used_count', 'created_at', 'updated_at', 'is_valid_display')
    inlines = [DiscountUsageInline]
    
    fieldsets = (
        ("اطلاعات اصلی", {
            "fields": ("code", "discount_type", "value", "club", "source_type")
        }),
        ("محدودیت‌ها", {
            "fields": ("usage_limit", "per_user_limit", "start_date", "end_date")
        }),
        ("وضعیت", {
            "fields": ("is_active", "is_valid_display", "used_count")
        }),
        ("تاریخ‌ها", {
            "fields": ("created_at", "updated_at")
        }),
    )
    
    def is_valid_display(self, obj):
        now = timezone.now()
        if not obj.is_active:
            return False
        if obj.start_date and obj.start_date > now:
            return False
        if obj.end_date and obj.end_date < now:
            return False
        if obj.usage_limit and obj.used_count >= obj.usage_limit:
            return False
        return True
    is_valid_display.short_description = "معتبر"
    is_valid_display.boolean = True


@admin.register(DiscountUsage)
class DiscountUsageAdmin(admin.ModelAdmin):
    list_display = ('id', 'discount', 'user', 'user_phone', 'used_at')
    list_filter = ('used_at', 'discount__code')
    search_fields = ('discount__code', 'user__phone', 'user__full_name')
    readonly_fields = ("used_at",)
    ordering = ("-used_at",)
    
    def user_phone(self, obj):
        return obj.user.phone
    user_phone.short_description = "شماره تلفن"
