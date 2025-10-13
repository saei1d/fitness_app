from django.contrib import admin
from .models import DiscountCode, DiscountUsage


@admin.register(DiscountCode)
class DiscountCodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'discount_type', 'value', 'club', 'source_type', 'is_active', 'used_count', 'created_at')
    list_filter = ('discount_type', 'source_type', 'is_active', 'created_at')
    search_fields = ('code', 'club__name')
    readonly_fields = ('used_count', 'created_at', 'updated_at')


@admin.register(DiscountUsage)
class DiscountUsageAdmin(admin.ModelAdmin):
    list_display = ('id', 'discount', 'user', 'used_at')
    list_filter = ('used_at',)
    search_fields = ('discount__code', 'user__phone')
