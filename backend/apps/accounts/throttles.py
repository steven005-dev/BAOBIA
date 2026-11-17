"""Limitation des essais de connexion (anti force brute).

Deux limites indépendantes, toutes deux comptées à chaque essai :
- par numéro de téléphone (normalisé : "07 07..." et "+225 07..." comptent ensemble) ;
- par adresse IP (plus large : plusieurs éleveurs partagent souvent la même IP mobile).
Taux réglés dans settings : DEFAULT_THROTTLE_RATES["login_phone"] et ["login_ip"].
"""

from django.core.exceptions import ValidationError
from rest_framework.settings import api_settings
from rest_framework.throttling import SimpleRateThrottle

from .validators import normalize_phone


class _SettingsRateThrottle(SimpleRateThrottle):
    def get_rate(self):
        # Lu à chaque requête (DRF le fige sinon au premier import).
        return api_settings.DEFAULT_THROTTLE_RATES[self.scope]


class LoginIPThrottle(_SettingsRateThrottle):
    scope = "login_ip"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class LoginPhoneThrottle(_SettingsRateThrottle):
    scope = "login_phone"

    def get_cache_key(self, request, view):
        data = request.data if hasattr(request.data, "get") else {}
        raw = str(data.get("phone", ""))[:40]
        try:
            ident = normalize_phone(raw)
        except ValidationError:
            ident = "".join(raw.split()).lower()
        return self.cache_format % {"scope": self.scope, "ident": ident or "empty"}
