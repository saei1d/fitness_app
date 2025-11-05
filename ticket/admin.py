from django.contrib import admin
from .models import Ticket, TicketMessage


class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 1
    readonly_fields = ("created_at",)
    fields = ("author", "message", "created_at")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'creator', 'creator_phone', 'admin', 'admin_phone', 'status', 'messages_count', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at', 'updated_at')
    search_fields = ('subject', 'creator__phone', 'creator__full_name', 'admin__phone', 'admin__full_name')
    readonly_fields = ('created_at', 'updated_at', 'messages_count')
    inlines = [TicketMessageInline]
    
    fieldsets = (
        ("اطلاعات تیکت", {
            "fields": ("subject", "creator", "admin", "status")
        }),
        ("آمار", {
            "fields": ("messages_count",)
        }),
        ("تاریخ‌ها", {
            "fields": ("created_at", "updated_at")
        }),
    )
    
    actions = ["assign_to_admin", "mark_as_resolved", "mark_as_closed"]
    
    def creator_phone(self, obj):
        return obj.creator.phone
    creator_phone.short_description = "شماره تلفن سازنده"
    
    def admin_phone(self, obj):
        return obj.admin.phone if obj.admin else "-"
    admin_phone.short_description = "شماره تلفن ادمین"
    
    def messages_count(self, obj):
        return obj.messages.count()
    messages_count.short_description = "تعداد پیام‌ها"
    
    def assign_to_admin(self, request, queryset):
        queryset.update(admin=request.user)
    assign_to_admin.short_description = "اختصاص به ادمین جاری"
    
    def mark_as_resolved(self, request, queryset):
        queryset.update(status='resolved')
    mark_as_resolved.short_description = "علامت‌گذاری به عنوان حل شده"
    
    def mark_as_closed(self, request, queryset):
        queryset.update(status='closed')
    mark_as_closed.short_description = "علامت‌گذاری به عنوان بسته شده"


@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'ticket_subject', 'author', 'author_phone', 'message_short', 'created_at')
    list_filter = ('created_at', 'ticket__status')
    search_fields = ('ticket__subject', 'author__phone', 'author__full_name', 'message')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    fieldsets = (
        ("اطلاعات پیام", {
            "fields": ("ticket", "author", "message")
        }),
        ("تاریخ", {
            "fields": ("created_at",)
        }),
    )
    
    def ticket_subject(self, obj):
        return obj.ticket.subject
    ticket_subject.short_description = "موضوع تیکت"
    
    def author_phone(self, obj):
        return obj.author.phone
    author_phone.short_description = "شماره تلفن نویسنده"
    
    def message_short(self, obj):
        if obj.message:
            return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message
        return "-"
    message_short.short_description = "پیام"
