from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError


def validate_avatar_size(value):
    """Validate avatar file size (max 5MB)"""
    max_size = 5 * 1024 * 1024  # 5MB
    if value.size > max_size:
        raise ValidationError(f'Avatar file size must be less than 5MB. Current size: {value.size / (1024*1024):.2f}MB')


def validate_banner_size(value):
    """Validate banner file size (max 10MB)"""
    max_size = 10 * 1024 * 1024  # 10MB
    if value.size > max_size:
        raise ValidationError(f'Banner file size must be less than 10MB. Current size: {value.size / (1024*1024):.2f}MB')


def validate_gym_image_size(value):
    """Validate gym image file size (max 10MB)"""
    max_size = 10 * 1024 * 1024  # 10MB
    if value.size > max_size:
        raise ValidationError(f'Gym image file size must be less than 10MB. Current size: {value.size / (1024*1024):.2f}MB')
