import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


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
