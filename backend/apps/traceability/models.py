from django.conf import settings
from django.db import models

from apps.core.models import (
    CorrectableMixin,
    DeclarationModel,
    EventModel,
    PositionMixin,
    UUIDModel,
)


class Movement(DeclarationModel):
    """
    Déclaration de mouvement (sortie d'un centre, vers un autre).
    Le statut et received_at sont des valeurs CALCULÉES (cache), gérées par services.py.
    Exigence : MV-01
    """

    MOVEMENT_TYPES = (
        ("transfer", "Transfert"),
        ("sale", "Vente"),
        ("slaughter", "Abattage"),
        ("temporary", "Temporaire"),
        ("return", "Retour"),
    )

    STATUS_CHOICES = (
        ("declared", "Déclaré"),
        ("confirmed", "Confirmé"),
        ("partial", "Partiel"),
        ("disputed", "Contesté"),
        ("cancelled", "Annulé"),
        ("expired", "Expiré"),
    )

    movement_type = models.CharField(max_length=10, choices=MOVEMENT_TYPES)
    from_center = models.ForeignKey(
        "identity.Center",
        on_delete=models.PROTECT,
        related_name="outgoing_movements",
    )
    to_center = models.ForeignKey(
        "identity.Center",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="incoming_movements",
    )
    to_party_note = models.CharField(max_length=160, null=True, blank=True)
    status = models.CharField(
        max_length=14,
        default="declared",
        choices=STATUS_CHOICES,
        editable=False,
    )
    expected_return_on = models.DateField(null=True, blank=True)
    planned_route = models.JSONField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        db_table = "movement"
        indexes = [
            models.Index(fields=("from_center", "occurred_at"), name="idx_mvt_from_occurred"),
            models.Index(fields=("to_center", "occurred_at"), name="idx_mvt_to_occurred"),
            models.Index(fields=("status",), name="idx_mvt_status"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    movement_type__in=("transfer", "sale", "slaughter", "temporary", "return")
                ),
                name="chk_movement_type",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=(
                        "declared",
                        "confirmed",
                        "partial",
                        "disputed",
                        "cancelled",
                        "expired",
                    )
                ),
                name="chk_movement_status",
            ),
            models.CheckConstraint(
                condition=models.Q(to_center__isnull=True)
                | ~models.Q(from_center=models.F("to_center")),
                name="chk_movement_different_centers",
            ),
        ]


class MovementItem(models.Model):
    """
    Association mouvement <-> unité suivie, avec quantités envoyées et reçues.
    Exigence : MV-01, MV-03
    """

    movement = models.ForeignKey(
        Movement,
        on_delete=models.CASCADE,
        related_name="items",
    )
    unit = models.ForeignKey(
        "identity.TrackedUnit",
        on_delete=models.PROTECT,
        related_name="movement_items",
    )
    pk = models.CompositePrimaryKey("movement_id", "unit_id")
    quantity_sent = models.PositiveIntegerField(default=1)
    quantity_received = models.PositiveIntegerField(null=True, blank=True)
    received_unit = models.ForeignKey(
        "identity.TrackedUnit",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="received_as_split",
    )

    class Meta:
        db_table = "movement_item"
        indexes = [
            models.Index(fields=("unit", "movement"), name="idx_mvt_item_unit_mvt"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity_sent__gt=0),
                name="chk_movement_item_qty_sent",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity_received__isnull=True)
                | models.Q(quantity_received__gte=0),
                name="chk_movement_item_qty_received",
            ),
        ]


class UnitOpenMovement(models.Model):
    """
    Verrou : une unité ne peut être que dans UN SEUL mouvement non terminé.
    Créé à la déclaration, supprimé à la clôture. Seule table métier avec suppression physique.
    Exigence : MV-02
    """

    unit = models.OneToOneField(
        "identity.TrackedUnit",
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="open_movement",
    )
    movement = models.ForeignKey(
        Movement,
        on_delete=models.CASCADE,
        related_name="locked_units",
    )
    since = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "unit_open_movement"


class MovementConfirmation(EventModel, PositionMixin):
    """
    Double confirmation : expéditeur puis destinataire (événement immuable).
    Exigence : MV-04, MV-05
    """

    SIDES = (
        ("sender", "Expéditeur"),
        ("receiver", "Destinataire"),
    )

    DECISIONS = (
        ("confirm", "Confirmer"),
        ("refuse", "Refuser"),
        ("confirm_with_discrepancy", "Confirmer avec écart"),
    )

    movement = models.ForeignKey(
        Movement,
        on_delete=models.CASCADE,
        related_name="confirmations",
    )
    side = models.CharField(max_length=8, choices=SIDES)
    decision = models.CharField(max_length=24, choices=DECISIONS)

    class Meta:
        db_table = "movement_confirmation"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(side__in=("sender", "receiver")),
                name="chk_movement_conf_side",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    decision__in=("confirm", "refuse", "confirm_with_discrepancy")
                ),
                name="chk_movement_conf_decision",
            ),
            models.UniqueConstraint(
                fields=("movement", "side"),
                name="uniq_movement_confirmation_side",
            ),
        ]


class MovementConfirmationCode(UUIDModel):
    """
    Code à usage unique que le destinataire saisit pour confirmer la réception.
    Le code est stocké haché (code_hash).
    Exigence : MV-07
    """

    movement = models.ForeignKey(
        Movement,
        on_delete=models.CASCADE,
        related_name="confirmation_codes",
    )
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "movement_confirmation_code"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(attempts__lte=5),
                name="chk_movement_conf_code_attempts",
            )
        ]


class MovementDiscrepancy(DeclarationModel):
    """
    Écart constaté au rapprochement lors de la réception (manquant, en trop...).
    Exigence : MV-06
    """

    KINDS = (
        ("missing", "Manquant"),
        ("extra", "En trop"),
        ("count_mismatch", "Écart de nombre"),
        ("identity_mismatch", "Écart d'identité"),
    )

    STATUS_CHOICES = (
        ("open", "Ouvert"),
        ("resolved", "Résolu"),
    )

    movement = models.ForeignKey(
        Movement,
        on_delete=models.CASCADE,
        related_name="discrepancies",
    )
    unit = models.ForeignKey(
        "identity.TrackedUnit",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    kind = models.CharField(max_length=18, choices=KINDS)
    quantity_expected = models.PositiveIntegerField(null=True, blank=True)
    quantity_found = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=8, default="open", choices=STATUS_CHOICES)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "movement_discrepancy"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    kind__in=("missing", "extra", "count_mismatch", "identity_mismatch")
                ),
                name="chk_movement_discrepancy_kind",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=("open", "resolved")),
                name="chk_movement_discrepancy_status",
            ),
        ]


class MovementStatusEvent(EventModel):
    """
    Journal des changements de statut d'un mouvement (événement immuable, append-only).
    Exigence : MV-08
    """

    movement = models.ForeignKey(
        Movement,
        on_delete=models.CASCADE,
        related_name="status_events",
    )
    status = models.CharField(max_length=14)
    reason = models.CharField(max_length=160, null=True, blank=True)

    class Meta:
        db_table = "movement_status_event"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    status__in=(
                        "declared",
                        "confirmed",
                        "partial",
                        "disputed",
                        "cancelled",
                        "expired",
                    )
                ),
                name="chk_movement_status_event_status",
            )
        ]


class StatusEvent(EventModel, CorrectableMixin, PositionMixin):
    """
    Événements de vie d'une unité : naissance, décès, abattage, disparition, vol...
    Événement immuable, corrigeable par un nouvel événement référençant le précédent.
    Exigence : MV-08, MV-09
    """

    EVENT_TYPES = (
        ("birth", "Naissance"),
        ("death", "Décès"),
        ("slaughter", "Abattage"),
        ("missing", "Disparition"),
        ("found", "Retrouvé"),
        ("size_change", "Changement d'effectif"),
        ("stolen_declared", "Vol déclaré"),
        ("stolen_lifted", "Vol levé"),
        ("merge", "Fusion"),
    )

    VISIBILITIES = (
        ("owner", "Propriétaire"),
        ("professionals", "Professionnels"),
        ("all", "Tous"),
    )

    unit = models.ForeignKey(
        "identity.TrackedUnit",
        on_delete=models.PROTECT,
        related_name="status_events",
    )
    event_type = models.CharField(max_length=16, choices=EVENT_TYPES)
    payload = models.JSONField(default=dict)
    visibility = models.CharField(max_length=14, default="owner", choices=VISIBILITIES)

    class Meta:
        db_table = "status_event"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    event_type__in=(
                        "birth",
                        "death",
                        "slaughter",
                        "missing",
                        "found",
                        "size_change",
                        "stolen_declared",
                        "stolen_lifted",
                        "merge",
                    )
                ),
                name="chk_status_event_type",
            ),
            models.CheckConstraint(
                condition=models.Q(visibility__in=("owner", "professionals", "all")),
                name="chk_status_event_visibility",
            ),
            models.UniqueConstraint(
                fields=("supersedes",),
                condition=models.Q(supersedes__isnull=False),
                name="uniq_status_event_supersedes",
            ),
        ]


class RfidTag(UUIDModel):
    """
    Boucle d'oreille officielle RFID (Vet'Tronic, norme ISO 11784/11785) portée par une unité.
    Numéro de 15 chiffres : 3 chiffres de pays (384 = Côte d'Ivoire) + 12 chiffres.
    Le téléphone ne lit pas la puce : le numéro arrive par saisie, par scan du code imprimé,
    ou plus tard par un lecteur RFID (read_mode). Rien ne s'efface : une boucle perdue ou
    remplacée change de statut, une nouvelle est ajoutée.
    Guide de réalisation des ajouts (Romuald, 21/11), ajout 1.
    """

    READ_MODES = (
        ("rfid_reader", "Lecteur RFID"),
        ("code_scan", "Scan du code imprimé"),
        ("manual_entry", "Saisie manuelle"),
    )
    STATUS_CHOICES = (
        ("active", "Active"),
        ("lost", "Perdue"),
        ("replaced", "Remplacée"),
    )

    unit = models.ForeignKey(
        "identity.TrackedUnit", on_delete=models.PROTECT, related_name="rfid_tags"
    )
    number = models.CharField(max_length=15)
    read_mode = models.CharField(max_length=12, choices=READ_MODES)
    status = models.CharField(max_length=8, default="active", choices=STATUS_CHOICES)
    fitted_at = models.DateTimeField()
    fitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    ended_at = models.DateTimeField(null=True, blank=True)
    is_simulated = models.BooleanField(default=False)

    class Meta:
        db_table = "rfid_tag"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(number__regex=r"^\d{15}$"), name="chk_rfid_tag_number"
            ),
            models.CheckConstraint(
                condition=models.Q(read_mode__in=("rfid_reader", "code_scan", "manual_entry")),
                name="chk_rfid_tag_read_mode",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=("active", "lost", "replaced")),
                name="chk_rfid_tag_status",
            ),
            # Un numéro n'est actif que sur une seule unité ; une unité n'a qu'une boucle active.
            models.UniqueConstraint(
                fields=("number",), condition=models.Q(status="active"),
                name="uniq_rfid_tag_active_number",
            ),
            models.UniqueConstraint(
                fields=("unit",), condition=models.Q(status="active"),
                name="uniq_rfid_tag_active_unit",
            ),
        ]


class MarketScan(EventModel, PositionMixin):
    """
    Un passage scanné à l'Entrée ou à la Sortie d'un marché (ajouts 2, 3 et 5 du guide).
    Garde aussi les codes inconnus : le bilan du jour les compte. `id` créé par l'appareil
    (rejouer le même scan est sans effet). Événement immuable.
    """

    DIRECTIONS = (("in", "Entrée"), ("out", "Sortie"))
    RESULTS = (
        ("ok", "Animal retrouvé"),
        ("unknown", "Code inconnu"),
        ("already_scanned", "Déjà scanné"),
        ("refused", "Refusé"),
    )

    market = models.ForeignKey(
        "identity.Center", on_delete=models.PROTECT, related_name="market_scans"
    )
    direction = models.CharField(max_length=3, choices=DIRECTIONS)
    code = models.CharField(max_length=40)
    unit = models.ForeignKey(
        "identity.TrackedUnit", null=True, blank=True, on_delete=models.PROTECT,
        related_name="market_scans",
    )
    result = models.CharField(max_length=16, choices=RESULTS)
    reason = models.CharField(max_length=160, null=True, blank=True)
    warning_code = models.CharField(max_length=30, null=True, blank=True)
    movement = models.ForeignKey(
        Movement, null=True, blank=True, on_delete=models.PROTECT, related_name="market_scans"
    )
    origin_zone = models.ForeignKey(
        "geo.Zone", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )

    class Meta:
        db_table = "market_scan"
        indexes = [
            models.Index(fields=("market", "occurred_at"), name="idx_market_scan_day"),
            models.Index(fields=("unit", "occurred_at"), name="idx_market_scan_unit"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(direction__in=("in", "out")), name="chk_market_scan_direction"
            ),
            models.CheckConstraint(
                condition=models.Q(result__in=("ok", "unknown", "already_scanned", "refused")),
                name="chk_market_scan_result",
            ),
        ]
