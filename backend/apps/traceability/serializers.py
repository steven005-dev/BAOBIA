import uuid
from rest_framework import serializers

from apps.identity.models import Center, TrackedUnit
from apps.traceability.models import (
    Movement,
    MovementConfirmation,
    MovementDiscrepancy,
    MovementItem,
    MovementStatusEvent,
)


class MovementItemInputSerializer(serializers.Serializer):
    unit_id = serializers.UUIDField()
    quantity_sent = serializers.IntegerField(default=1, min_value=1)


class MovementItemReadSerializer(serializers.ModelSerializer):
    unit_kind = serializers.CharField(source="unit.kind", read_only=True)
    unit_local_name = serializers.CharField(source="unit.local_name", read_only=True)

    class Meta:
        model = MovementItem
        fields = ("unit", "unit_kind", "unit_local_name", "quantity_sent", "quantity_received")


class MovementStatusEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovementStatusEvent
        fields = ("id", "status", "reason", "occurred_at", "created_at")


class MovementConfirmationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovementConfirmation
        fields = ("id", "side", "decision", "occurred_at", "created_at")


class MovementDetailSerializer(serializers.ModelSerializer):
    items = MovementItemReadSerializer(many=True, read_only=True)
    status_events = MovementStatusEventSerializer(many=True, read_only=True)
    confirmations = MovementConfirmationSerializer(many=True, read_only=True)
    from_center_name = serializers.CharField(source="from_center.name", read_only=True)
    to_center_name = serializers.CharField(source="to_center.name", read_only=True)

    class Meta:
        model = Movement
        fields = (
            "id",
            "movement_type",
            "from_center",
            "from_center_name",
            "to_center",
            "to_center_name",
            "to_party_note",
            "status",
            "occurred_at",
            "received_at",
            "expected_return_on",
            "is_simulated",
            "items",
            "status_events",
            "confirmations",
            "created_at",
        )


class MovementCreateSerializer(serializers.Serializer):
    """
    Sérialiseur de création de mouvement.
    Règle 4 : Accepte un UUID 'id' ou 'operation_id' généré par l'appareil hors ligne.
    """

    id = serializers.UUIDField(required=False, default=uuid.uuid4)
    operation_id = serializers.UUIDField(required=False)
    movement_type = serializers.ChoiceField(
        choices=("transfer", "sale", "slaughter", "temporary", "return"),
        default="transfer",
    )
    from_center_id = serializers.UUIDField()
    to_center_id = serializers.UUIDField(required=False, allow_null=True)
    to_party_note = serializers.CharField(max_length=160, required=False, allow_blank=True)
    occurred_at = serializers.DateTimeField(required=False)
    items = MovementItemInputSerializer(many=True, allow_empty=False)

    def validate(self, attrs):
        from_id = attrs.get("from_center_id")
        to_id = attrs.get("to_center_id")

        if to_id and from_id == to_id:
            raise serializers.ValidationError(
                {"to_center_id": "L'élevage de destination doit être différent de l'élevage de départ."}
            )

        # Vérifier l'existence de from_center
        if not Center.objects.filter(id=from_id).exists():
            raise serializers.ValidationError({"from_center_id": "Élevage de départ introuvable."})

        if to_id and not Center.objects.filter(id=to_id).exists():
            raise serializers.ValidationError({"to_center_id": "Élevage destinataire introuvable."})

        return attrs
