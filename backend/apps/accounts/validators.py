import re

from django.core.exceptions import ValidationError


E164_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")


def normalize_phone(value):
    """Return a canonical E.164 phone number or raise ValidationError."""
    phone = str(value or "").strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+") and phone.isdigit():
        phone = f"+{phone}"
    if not E164_PATTERN.fullmatch(phone):
        raise ValidationError("Numéro de téléphone invalide.")
    return phone


def validate_phone(value):
    normalize_phone(value)
