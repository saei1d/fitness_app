from django.contrib import admin
from .models import Review, Favorite


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "gym", "rating", "is_reported", "buyer", "blocked", "deleted", "created_at")
    list_filter = ("rating", "is_reported", "buyer", "blocked", "deleted", "created_at")
    search_fields = ("user__phone", "gym__name")


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "gym")
    search_fields = ("user__phone", "gym__name")
