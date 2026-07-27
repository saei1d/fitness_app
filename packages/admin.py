from django.contrib import admin
from .models import Package, GroupPackage


class PackageInline(admin.TabularInline):
    model = Package
    extra = 1
    fields = ("title", "description", "gender", "price", "duration", "commission_rate", "order_homepage", "dedicated")


@admin.register(GroupPackage)
class GroupPackageAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "description", "packages_count")
    search_fields = ("title", "description")
    inlines = [PackageInline]
    
    def packages_count(self, obj):
        return obj.packages.count()
    packages_count.short_description = "تعداد پکیج‌ها"


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "group_package", "gym", "gender", "price", "duration", "commission_rate", "order_homepage", "dedicated", "purchases_count")
    search_fields = ("title", "description", "group_package__title", "gym__name")
    list_filter = ("gender", "gym", "duration", "dedicated")
    readonly_fields = ("purchases_count",)

    fieldsets = (
        ("اطلاعات اصلی", {
            "fields": ("gym", "group_package", "title", "description")
        }),
        ("جزئیات پکیج", {
            "fields": ("gender", "price", "duration", "commission_rate", "order_homepage", "dedicated")
        }),
        ("آمار", {
            "fields": ("purchases_count",)
        }),
    )
    
    def purchases_count(self, obj):
        return obj.purchases.count()
    purchases_count.short_description = "تعداد خریدها"
