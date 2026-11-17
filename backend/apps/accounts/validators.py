"""Validateur unique du numéro de téléphone (format E.164).

Toute l'application passe par `normalize_phone` : modèle User, connexion,
limitation des essais, données de départ. Ne pas écrire d'autre règle ailleurs.
"""

import re

from django.conf import settings
from django.core.exceptions import ValidationError

E164_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")
# Caractères que les gens tapent ou dictent autour d'un numéro.
_SEPARATORS = re.compile(r"[\s\-.()/]")
NATIONAL_LENGTH = 10  # Côte d'Ivoire : 10 chiffres depuis 2021 (07 07 07 07 07)


def normalize_phone(value):
    """Retourne le numéro au format E.164 (+225...) ou lève ValidationError.

    Formats acceptés : "+225 07 07 07 07 07", "00225 0707070707",
    "2250707070707", "07 07 07 07 07" (numéro national, indicatif ajouté).
    """
    phone = _SEPARATORS.sub("", str(value or ""))
    if phone.isdigit():
        if len(phone) == NATIONAL_LENGTH and phone.startswith("0"):
            phone = f"+{settings.PHONE_DEFAULT_COUNTRY_CODE}{phone}"  # national d'abord
        elif phone.startswith("00"):
            phone = "+" + phone[2:]
        else:
            phone = f"+{phone}"
    if not E164_PATTERN.fullmatch(phone):
        raise ValidationError("Numéro de téléphone invalide.", code="invalid_phone")
    return phone


def validate_phone(value):
    """Validateur de champ Django : refuse un numéro qui n'est pas déjà en E.164."""
    if normalize_phone(value) != value:
        raise ValidationError("Numéro de téléphone invalide.", code="invalid_phone")
