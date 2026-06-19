from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display    = ('recipient', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter     = ('notification_type', 'is_read', 'recipient')
    search_fields   = ('recipient__phone', 'title', 'message')
    ordering        = ('-created_at',)
    readonly_fields = ('created_at',)
    date_hierarchy  = 'created_at'

    fieldsets = (
        ("اطلاعات اعلان", {
            "fields": ("recipient", "notification_type", "title", "message", "data")
        }),
        ("وضعیت", {
            "fields": ("is_read",)
        }),
        ("تاریخ", {
            "fields": ("created_at",)
        }),
    )
