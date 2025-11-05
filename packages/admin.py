from django.contrib import admin
from .models import Package, GroupPackage


class PackageInline(admin.TabularInline):
    model = Package
    extra = 1
    fields = ("title", "description", "gender", "price", "duration", "commission_rate")


@admin.register(GroupPackage)
class GroupPackageAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "gym", "description", "packages_count")
    search_fields = ("title", "gym__name", "description")
    list_filter = ("gym",)
    inlines = [PackageInline]
    
    def packages_count(self, obj):
        return obj.packages.count()
    packages_count.short_description = "تعداد پکیج‌ها"


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "group_package", "gym_name", "gender", "price", "duration", "commission_rate", "purchases_count")
    search_fields = ("title", "description", "group_package__title", "group_package__gym__name")
    list_filter = ("gender", "group_package__gym", "duration")
    readonly_fields = ("purchases_count",)
    
    fieldsets = (
        ("اطلاعات اصلی", {
            "fields": ("group_package", "title", "description")
        }),
        ("جزئیات پکیج", {
            "fields": ("gender", "price", "duration", "commission_rate")
        }),
        ("آمار", {
            "fields": ("purchases_count",)
        }),
    )
    
    def gym_name(self, obj):
        return obj.group_package.gym.name if obj.group_package else "-"
    gym_name.short_description = "باشگاه"
    
    def purchases_count(self, obj):
        return obj.purchases.count()
    purchases_count.short_description = "تعداد خریدها"
