from django.contrib import admin
from .models import Review, Favorite


class ReviewReplyInline(admin.TabularInline):
    model = Review
    fk_name = "reply_to"
    extra = 0
    readonly_fields = ("user", "gym", "rating", "comment", "created_at")
    fields = ("user", "gym", "rating", "comment", "created_at", "blocked", "deleted")
    can_delete = False


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "user_phone", "gym", "rating", "comment_short", "is_reported", "buyer", "blocked", "deleted", "reply_to", "created_at")
    list_filter = ("rating", "is_reported", "buyer", "blocked", "deleted", "created_at")
    search_fields = ("user__phone", "user__full_name", "gym__name", "comment")
    readonly_fields = ("created_at",)
    inlines = [ReviewReplyInline]
    
    fieldsets = (
        ("اطلاعات اصلی", {
            "fields": ("user", "gym", "rating", "comment", "reply_to")
        }),
        ("وضعیت", {
            "fields": ("is_reported", "buyer", "blocked", "deleted")
        }),
        ("تاریخ", {
            "fields": ("created_at",)
        }),
    )
    
    actions = ["block_reviews", "unblock_reviews", "mark_as_reported", "mark_as_deleted"]
    
    def user_phone(self, obj):
        return obj.user.phone
    user_phone.short_description = "شماره تلفن"
    
    def comment_short(self, obj):
        if obj.comment:
            return obj.comment[:50] + "..." if len(obj.comment) > 50 else obj.comment
        return "-"
    comment_short.short_description = "نظر"
    
    def block_reviews(self, request, queryset):
        queryset.update(blocked=True)
    block_reviews.short_description = "مسدود کردن نظرات انتخاب شده"
    
    def unblock_reviews(self, request, queryset):
        queryset.update(blocked=False)
    unblock_reviews.short_description = "رفع مسدودیت نظرات انتخاب شده"
    
    def mark_as_reported(self, request, queryset):
        queryset.update(is_reported=True)
    mark_as_reported.short_description = "علامت‌گذاری به عنوان گزارش شده"
    
    def mark_as_deleted(self, request, queryset):
        queryset.update(deleted=True)
    mark_as_deleted.short_description = "علامت‌گذاری به عنوان حذف شده"


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "user_phone", "gym", "gym_owner")
    search_fields = ("user__phone", "user__full_name", "gym__name")
    list_filter = ("gym",)
    
    def user_phone(self, obj):
        return obj.user.phone
    user_phone.short_description = "شماره تلفن"
    
    def gym_owner(self, obj):
        return obj.gym.owner.phone if obj.gym.owner else "-"
    gym_owner.short_description = "مالک باشگاه"
