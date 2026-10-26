import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def convert_persian_to_english_digits(text):
    """
    Convert Persian digits to English digits
    """
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    english_digits = '0123456789'
    
    translation_table = str.maketrans(persian_digits, english_digits)
    return text.translate(translation_table)


def validate_iranian_phone_number(value):
    """
    Validate Iranian phone number format (09xxxxxxxxx)
    """
    if not re.match(r'^09[0-9]{9}$', value):
        raise ValidationError(
            _('Phone number must be in format 09xxxxxxxxx (11 digits starting with 09)'),
            code='invalid_phone_format'
        )
    return value


def validate_card_number(value):
    """
    Validate bank card number (16 to 20 digits).
    Persian/Arabic digits and separators (space, dash) are normalized before validation.
    """
    if value in (None, ''):
        return value

    normalized = convert_persian_to_english_digits(str(value))
    normalized = re.sub(r'[\s-]', '', normalized)
    if not re.fullmatch(r'[0-9]{16,20}', normalized):
        raise ValidationError(
            _('Card number must contain 16 to 20 digits.'),
            code='invalid_card_number'
        )
    return value
