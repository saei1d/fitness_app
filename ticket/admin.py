from django.contrib import admin
from .models import Ticket, TicketMessage

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'creator', 'admin', 'status', 'created_at')  # priority حذف شد
    list_filter = ('status', 'created_at')  # قبلا priority هم بود
    search_fields = ('subject', 'creator__phone', 'admin__phone')

@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'author', 'created_at')  # is_internal حذف شد
    list_filter = ('created_at',)  # is_internal حذف شد
    search_fields = ('ticket__subject', 'author__phone')
