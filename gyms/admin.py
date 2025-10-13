from django.contrib import admin
from .models import Gym, GymImage


@admin.register(Gym)
class GymAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner", "average_rating", "comments", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "owner__phone")


@admin.register(GymImage)
class GymImageAdmin(admin.ModelAdmin):
    list_display = ("id", "gym", "order", "uploaded_at")
    list_filter = ("uploaded_at",)
    search_fields = ("gym__name",)
