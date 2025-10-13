from django.contrib import admin
from .models import Package, GroupPackage


@admin.register(GroupPackage)
class GroupPackageAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "gym", "description")
    search_fields = ("title", "gym__name")


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "group_package", "gender", "price", "duration", "commission_rate")
    search_fields = ("title", "group_package__title", "group_package__gym__name")
    list_filter = ("gender", "group_package__gym")
