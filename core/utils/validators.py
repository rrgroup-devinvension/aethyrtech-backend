import re
from django.core.exceptions import ValidationError

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

def validate_uuid(value: str):
    if not UUID_RE.match(str(value)):
        raise ValidationError("Invalid UUID format.")

PHONE_E164_RE = re.compile(r"^\+?[1-9]\d{7,14}$")

def validate_phone_e164(value: str):
    if not PHONE_E164_RE.match(str(value)):
        raise ValidationError("Invalid phone number (E.164 expected).")
