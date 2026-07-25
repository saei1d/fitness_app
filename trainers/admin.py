from django.contrib import admin
from django import forms
from .models import Trainer, TrainerGroupPackage, TrainerPackage, TrainerReview
import json


class TrainerAdminForm(forms.ModelForm):
    class Meta:
        model = Trainer
        fields = '__all__'

    def clean_specializations(self):
        data = self.cleaned_data.get('specializations')
        if isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                raise forms.ValidationError('Enter a valid JSON list.')
        return data

    def clean_certifications(self):
        data = self.cleaned_data.get('certifications')
        if isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                raise forms.ValidationError('Enter a valid JSON list.')
        return data

    def clean_special_expertise(self):
        data = self.cleaned_data.get('special_expertise')
        if isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                raise forms.ValidationError('Enter a valid JSON list.')
        return data


@admin.register(Trainer)
class TrainerAdmin(admin.ModelAdmin):
    form = TrainerAdminForm
    list_display = ['name', 'phone', 'average_rating', 'reviews_count', 'active_students_count', 'order_homepage', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'phone', 'bio']
    filter_horizontal = ['active_gyms']
    readonly_fields = ['average_rating', 'reviews_count', 'created_at', 'updated_at']
    list_editable = ['order_homepage']


@admin.register(TrainerGroupPackage)
class TrainerGroupPackageAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'trainer',
        'created_at',
        'updated_at',
    ]
    list_filter = [
        'created_at',
    ]
    search_fields = [
        'title',
        'trainer__name',
    ]
    readonly_fields = [
        'created_at',
        'updated_at',
    ]


@admin.register(TrainerPackage)
class TrainerPackageAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'group_package',
        'gender',
        'price',
        'duration',
        'sessions',
        'order_homepage',
        'created_at',
    ]
    list_filter = [
        'gender',
        'created_at',
    ]
    search_fields = [
        'title',
        'group_package__title',
        'group_package__trainer__name',
    ]
    readonly_fields = [
        'created_at',
        'updated_at',
    ]
    
@admin.register(TrainerReview)
class TrainerReviewAdmin(admin.ModelAdmin):
    list_display = ['trainer', 'user', 'rating', 'buyer', 'is_reported', 'blocked', 'deleted', 'created_at']
    list_filter = ['rating', 'buyer', 'is_reported', 'blocked', 'deleted', 'created_at']
    search_fields = ['trainer__name', 'user__phone', 'comment']
    readonly_fields = ['created_at']
