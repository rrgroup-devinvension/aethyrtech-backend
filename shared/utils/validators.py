import re

from rest_framework.exceptions import ValidationError


def validate_phone_number(value):
    """Universal validator for phone numbers."""
    if not re.match(r"^\+?1?\d{9,15}$", value):
        raise ValidationError("Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    return value
