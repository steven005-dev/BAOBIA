"""Formes des données des routes /api/notifications/."""

from rest_framework import serializers


class NotificationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.CharField(help_text="exposure, alert, zone_cluster_review, escalation")
    message_code = serializers.CharField(help_text="Gabarit du texte (vocabulaire officiel de l'application).")
    params = serializers.DictField(help_text="Valeurs simples à insérer ; jamais d'élevage d'origine.")
    alert_id = serializers.UUIDField(allow_null=True)
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    read_at = serializers.DateTimeField(allow_null=True)


class UnreadCountSerializer(serializers.Serializer):
    unread = serializers.IntegerField()


class MarkReadSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, allow_empty=False,
        help_text="Messages à marquer lus. Absent : tous mes messages.",
    )


class MarkedSerializer(serializers.Serializer):
    marked = serializers.IntegerField()
