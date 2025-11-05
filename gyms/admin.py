from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import Gym, GymImage


class GymImageInline(admin.TabularInline):
    model = GymImage
    extra = 1
    fields = ("image", "alt_text", "order")
    ordering = ("order",)


@admin.register(Gym)
class GymAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner", "address", "average_rating", "comments", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at", "average_rating")
    search_fields = ("name", "owner__phone", "address", "description")
    readonly_fields = ("created_at", "updated_at", "average_rating", "comments", "latitude", "longitude")
    filter_horizontal = ()
    inlines = [GymImageInline]
    
    fieldsets = (
        ("اطلاعات اصلی", {
            "fields": ("name", "owner", "description", "address")
        }),
        ("موقعیت جغرافیایی", {
            "fields": ("location", "latitude", "longitude")
        }),
        ("اطلاعات اضافی", {
            "fields": ("working_hours", "banner", "average_rating", "comments")
        }),
        ("تاریخ‌ها", {
            "fields": ("created_at", "updated_at")
        }),
    )


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
