import uuid
from datetime import timedelta

from rest_framework import serializers

from apps.identity.models import Center, TrackedUnit
from apps.traceability.models import (
    Movement,
    MovementConfirmation,
    MovementDiscrepancy,
    MovementItem,
    MovementStatusEvent,
    StatusEvent,
)
from apps.traceability.services import UNIT_EVENT_TYPES, confirmation_mode


class MovementItemInputSerializer(serializers.Serializer):
    unit_id = serializers.UUIDField()
    quantity_sent = serializers.IntegerField(default=1, min_value=1)


class ReceivedItemSerializer(serializers.Serializer):
    unit_id = serializers.UUIDField()
    quantity_received = serializers.IntegerField(min_value=0)


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


# Au-delà, une date envoyée par le téléphone dans le futur signale une horloge fausse.
CLOCK_TOLERANCE = timedelta(minutes=10)


def is_clock_suspect(occurred_at, created_at):
    return bool(occurred_at and created_at and occurred_at > created_at + CLOCK_TOLERANCE)


class MovementConfirmationSerializer(serializers.ModelSerializer):
    mode = serializers.SerializerMethodField(
        help_text="direct : membre de l'élevage ; assisted : agent mandaté (MV-04)."
    )
    entered_by_name = serializers.CharField(source="created_by.full_name", read_only=True)
    clock_suspect = serializers.SerializerMethodField()

    class Meta:
        model = MovementConfirmation
        fields = ("id", "side", "decision", "mode", "entered_by_name", "occurred_at",
                  "created_at", "clock_suspect")

    def get_mode(self, obj):
        movement = obj.movement
        center_id = movement.from_center_id if obj.side == "sender" else movement.to_center_id
        return confirmation_mode(obj.created_by, center_id, at=obj.created_at)

    def get_clock_suspect(self, obj):
        return is_clock_suspect(obj.occurred_at, obj.created_at)


class MovementDiscrepancySerializer(serializers.ModelSerializer):
    unit_local_name = serializers.CharField(source="unit.local_name", read_only=True,
                                            allow_null=True)

    class Meta:
        model = MovementDiscrepancy
        fields = ("id", "unit", "unit_local_name", "kind", "quantity_expected",
                  "quantity_found", "status", "occurred_at")


class MovementDetailSerializer(serializers.ModelSerializer):
    items = MovementItemReadSerializer(many=True, read_only=True)
    status_events = MovementStatusEventSerializer(many=True, read_only=True)
    confirmations = MovementConfirmationSerializer(many=True, read_only=True)
    discrepancies = MovementDiscrepancySerializer(many=True, read_only=True)
    from_center_name = serializers.CharField(source="from_center.name", read_only=True)
    to_center_name = serializers.CharField(source="to_center.name", read_only=True)
    clock_suspect = serializers.SerializerMethodField(
        help_text="Vrai si la date du téléphone est dans le futur (horloge fausse)."
    )

    def get_clock_suspect(self, obj):
        return is_clock_suspect(obj.occurred_at, obj.created_at)

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
            "discrepancies",
            "clock_suspect",
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
    to_center_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Obligatoire pour un transfert ; facultatif pour une vente ou un abattage hors BAOBIA.",
    )
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

        if attrs.get("movement_type", "transfer") == "transfer" and not to_id:
            raise serializers.ValidationError(
                {"to_center_id": "Un transfert doit avoir un élevage destinataire enregistré."}
            )

        # Vérifier l'existence de from_center
        if not Center.objects.filter(id=from_id).exists():
            raise serializers.ValidationError({"from_center_id": "Élevage de départ introuvable."})

        if to_id and not Center.objects.filter(id=to_id).exists():
            raise serializers.ValidationError({"to_center_id": "Élevage destinataire introuvable."})

        return attrs


class MovementConfirmSerializer(serializers.Serializer):
    """Confirmation de réception (MV-04/05/07), soumise par le destinataire."""

    id = serializers.UUIDField(required=False, default=uuid.uuid4)
    center_id = serializers.UUIDField()
    code = serializers.RegexField(r"^\d{6}$", write_only=True)
    occurred_at = serializers.DateTimeField(required=False)
    items_received = ReceivedItemSerializer(
        many=True, required=False, default=list, max_length=500,
        help_text="Rapprochement (MV-06) : nombre reçu par unité ; absent = tout reçu.",
    )


class MovementRefuseSerializer(serializers.Serializer):
    """Refus de réception par le destinataire (MV-05, MV-09)."""

    id = serializers.UUIDField(required=False)
    center_id = serializers.UUIDField()
    reason = serializers.CharField(max_length=140)
    occurred_at = serializers.DateTimeField(required=False)


class MovementReasonSerializer(serializers.Serializer):
    """Annulation (élevage de départ) ou contestation (une des deux parties)."""

    center_id = serializers.UUIDField()
    reason = serializers.CharField(max_length=140)
    occurred_at = serializers.DateTimeField(required=False)


class MarketEntrySerializer(serializers.Serializer):
    """Entrée au marché (R2) : codes d'étiquettes scannés par l'agent du marché."""

    id = serializers.UUIDField(help_text="UUID de l'opération créé sur le téléphone.")
    market_id = serializers.UUIDField()
    label_codes = serializers.ListField(
        child=serializers.CharField(max_length=20), min_length=1, max_length=200
    )
    occurred_at = serializers.DateTimeField(required=False)


class MarketExitSerializer(MarketEntrySerializer):
    """Sortie du marché (R2) : vers un élevage inscrit ou un acheteur non inscrit."""

    to_center_id = serializers.UUIDField(required=False, allow_null=True)
    to_party_note = serializers.CharField(max_length=160, required=False, allow_blank=True)

    def validate(self, attrs):
        to_id = attrs.get("to_center_id")
        if to_id and not Center.objects.filter(id=to_id, status="active").exists():
            raise serializers.ValidationError({"to_center_id": "Élevage acheteur introuvable."})
        if not to_id and not (attrs.get("to_party_note") or "").strip():
            raise serializers.ValidationError(
                {"to_party_note": "Indiquez l'élevage acheteur ou décrivez l'acheteur."}
            )
        return attrs


class UnitEventCreateSerializer(serializers.Serializer):
    """Événement de vie d'une unité (MV-02). `id` créé par le téléphone."""

    id = serializers.UUIDField()
    center_id = serializers.UUIDField()
    unit_id = serializers.UUIDField()
    event_type = serializers.ChoiceField(choices=UNIT_EVENT_TYPES)
    occurred_at = serializers.DateTimeField(required=False)
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)


class UnitEventReadSerializer(serializers.ModelSerializer):
    clock_suspect = serializers.SerializerMethodField()

    class Meta:
        model = StatusEvent
        fields = ("id", "unit", "event_type", "visibility", "payload", "occurred_at",
                  "created_at", "clock_suspect")

    def get_clock_suspect(self, obj):
        return is_clock_suspect(obj.occurred_at, obj.created_at)


class DestinationShareCreateSerializer(serializers.Serializer):
    center_id = serializers.UUIDField()


class DestinationShareResolveSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=512, trim_whitespace=True)


class DestinationShareResultSerializer(serializers.Serializer):
    code = serializers.CharField()
    expires_in_days = serializers.IntegerField()


class ResolvedDestinationSerializer(serializers.Serializer):
    center_id = serializers.UUIDField()
    center_name = serializers.CharField()


class RfidTagCreateSerializer(serializers.Serializer):
    """Boucle RFID Vet'Tronic posée sur un animal (guide des ajouts, 1)."""

    id = serializers.UUIDField()
    unit_id = serializers.UUIDField()
    number = serializers.CharField(max_length=30, help_text="15 chiffres, espaces permis.")
    read_mode = serializers.ChoiceField(choices=("rfid_reader", "code_scan", "manual_entry"))
    occurred_at = serializers.DateTimeField(required=False)


class MarketScanSerializer(serializers.Serializer):
    """Un scan au marché (guide des ajouts, 2) : numéro de boucle ou code BAOBIA."""

    id = serializers.UUIDField(help_text="UUID du scan créé sur le téléphone.")
    direction = serializers.ChoiceField(choices=("in", "out"))
    code = serializers.CharField(max_length=40)
    scanned_at = serializers.DateTimeField(required=False)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False,
                                        allow_null=True, min_value=-90, max_value=90)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False,
                                         allow_null=True, min_value=-180, max_value=180)
    position_accuracy_m = serializers.DecimalField(max_digits=7, decimal_places=1,
                                                   required=False, allow_null=True, min_value=0)
    position_source = serializers.ChoiceField(choices=("gps", "network", "manual", "none"),
                                              default="none")
    to_center_id = serializers.UUIDField(required=False, allow_null=True)
    to_party_note = serializers.CharField(max_length=160, required=False, allow_blank=True)
