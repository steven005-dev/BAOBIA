"""Formes des données des routes /api/auth/ (entrées et réponses, pour le schéma API)."""

from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField(
        max_length=40, help_text="Numéro de téléphone. Ex. +2250700000000 ou 07 00 00 00 00."
    )
    password = serializers.CharField(
        max_length=128, write_only=True, trim_whitespace=False, style={"input_type": "password"}
    )


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField(help_text="Jeton d'accès, à envoyer : Authorization: Bearer <access>.")
    refresh = serializers.CharField(help_text="Jeton pour obtenir un nouvel accès (/api/auth/refresh/).")


class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class AccessSerializer(serializers.Serializer):
    access = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(help_text="Le jeton refresh à mettre en liste noire.")


class ErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()


class _RefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class _ZoneRefSerializer(_RefSerializer):
    code = serializers.CharField()


class MeRoleSerializer(serializers.Serializer):
    code = serializers.CharField()
    label_fr = serializers.CharField()
    organization = _RefSerializer(allow_null=True)
    zone = _ZoneRefSerializer(allow_null=True)


class MeCenterSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    center_type = serializers.CharField()
    zone_id = serializers.UUIDField()
    access = serializers.ChoiceField(
        choices=("holder", "co_holder", "worker", "mandate"),
        help_text="Pourquoi l'utilisateur a accès : membre du centre ou mandat.",
    )
    mandate_scope = serializers.CharField(allow_null=True)


class MeSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    phone = serializers.CharField()
    full_name = serializers.CharField()
    language = serializers.CharField()
    is_simulated = serializers.BooleanField(help_text="Compte de démonstration.")
    roles = MeRoleSerializer(many=True)
    has_valid_habilitation = serializers.BooleanField()
    accessible_centers = MeCenterSerializer(many=True)
