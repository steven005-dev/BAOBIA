"""Modèles du module alerts (responsable : Yéo).

Conformes à docs/BAOBIA_DB_SPEC.md, section 6, application `alerts`.
- DiseaseRule : règle sanitaire VERSIONNÉE ; aucune valeur sanitaire dans le code.
- Alert : niveaux 1, 2, 3 ; le niveau 3 exige un vétérinaire habilité (CHECK en base).
- AlertExposure / AlertExposureStep : élevages EXPOSÉS (jamais « contaminés ») ou
  écartés (cas négatif), avec le chemin qui l'explique.
- AlertReview, AlertEvent : événements en ajout seul.
- Investigation, Quarantine : P2, tables prévues mais non utilisées dans le prototype.
"""

from django.conf import settings
from django.db import models

from apps.core.models import EventModel, StateModel, UUIDModel


class DiseaseRule(UUIDModel):
    """Règle sanitaire versionnée. Une règle utilisée par une alerte n'est jamais
    modifiée (trigger) : on crée la version suivante."""

    disease = models.ForeignKey("health.Disease", on_delete=models.PROTECT, related_name="+")
    species = models.ForeignKey(
        "core.Species", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    version = models.IntegerField()
    lookback_days = models.IntegerField()
    lookforward_days = models.IntegerField()
    max_depth = models.SmallIntegerField()
    min_zone_effectif = models.IntegerField(default=5)
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    include_unconfirmed = models.BooleanField(default=True)
    cluster_window_days = models.IntegerField(default=7)
    cluster_min_reports = models.SmallIntegerField(default=3)
    cluster_min_ratio = models.DecimalField(max_digits=5, decimal_places=4, null=True,
                                            blank=True)
    escalation_hours = models.IntegerField(default=24)

    class Meta:
        db_table = "disease_rule"
        constraints = [
            models.CheckConstraint(condition=models.Q(version__gt=0),
                                   name="chk_disease_rule_version"),
            models.CheckConstraint(condition=models.Q(lookback_days__gte=0),
                                   name="chk_disease_rule_lookback"),
            models.CheckConstraint(condition=models.Q(lookforward_days__gte=0),
                                   name="chk_disease_rule_lookforward"),
            models.CheckConstraint(condition=models.Q(max_depth__gte=1, max_depth__lte=6),
                                   name="chk_disease_rule_max_depth"),
            models.CheckConstraint(condition=models.Q(min_zone_effectif__gte=1),
                                   name="chk_disease_rule_min_zone_effectif"),
            models.CheckConstraint(condition=models.Q(cluster_window_days__gt=0),
                                   name="chk_disease_rule_cluster_window"),
            models.CheckConstraint(condition=models.Q(cluster_min_reports__gte=2),
                                   name="chk_disease_rule_cluster_min_reports"),
            models.CheckConstraint(
                condition=models.Q(cluster_min_ratio__isnull=True)
                | models.Q(cluster_min_ratio__gt=0, cluster_min_ratio__lte=1),
                name="chk_disease_rule_cluster_ratio",
            ),
            models.CheckConstraint(condition=models.Q(escalation_hours__gt=0),
                                   name="chk_disease_rule_escalation"),
            models.CheckConstraint(
                condition=models.Q(valid_to__isnull=True)
                | models.Q(valid_to__gte=models.F("valid_from")),
                name="chk_disease_rule_valid_dates",
            ),
            models.UniqueConstraint(
                fields=("disease", "species", "version"), nulls_distinct=False,
                name="uniq_disease_rule_version",
            ),
        ]

    def __str__(self):
        return f"{self.disease_id} v{self.version}"


class Alert(StateModel):
    class TriggerKind(models.TextChoices):
        SINGLE_REPORT = "single_report", "Signalement"
        ZONE_CLUSTER = "zone_cluster", "Regroupement de zone"

    class Confidence(models.TextChoices):
        NORMAL = "normal", "Normale"
        REDUCED = "reduced", "Réduite"

    class Status(models.TextChoices):
        OPEN = "open", "Ouverte"
        MONITORING = "monitoring", "Surveillance"
        CLOSED = "closed", "Clôturée"
        CANCELLED = "cancelled", "Annulée"

    disease = models.ForeignKey(
        "health.Disease", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    rule = models.ForeignKey(DiseaseRule, on_delete=models.PROTECT, related_name="alerts")
    trigger_kind = models.CharField(max_length=14, choices=TriggerKind.choices,
                                    default=TriggerKind.SINGLE_REPORT)
    focus_center = models.ForeignKey(
        "identity.Center", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    zone = models.ForeignKey("geo.Zone", on_delete=models.PROTECT, related_name="+")
    species = models.ForeignKey(
        "core.Species", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    confidence = models.CharField(max_length=7, choices=Confidence.choices,
                                  default=Confidence.NORMAL)
    escalation_due_at = models.DateTimeField(null=True, blank=True, editable=False)
    level = models.SmallIntegerField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    opened_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
        related_name="+",
    )
    habilitation = models.ForeignKey(
        "accounts.Habilitation", null=True, blank=True, on_delete=models.PROTECT,
        related_name="+",
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    current_run_id = models.UUIDField(null=True, blank=True, editable=False)
    reports = models.ManyToManyField("health.HealthReport", through="AlertReport",
                                     related_name="+", blank=True)

    class Meta:
        db_table = "alert"
        indexes = [
            models.Index(fields=("status", "zone"), name="idx_alert_status_zone"),
            models.Index(fields=("trigger_kind", "status", "zone"),
                         name="idx_alert_trigger_status_zone"),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(level__in=(1, 2, 3)),
                                   name="chk_alert_level"),
            models.CheckConstraint(
                condition=models.Q(level__lt=3)
                | models.Q(validated_by__isnull=False, validated_at__isnull=False,
                           habilitation__isnull=False),
                name="chk_alert_level3_validated",
            ),
            models.CheckConstraint(
                condition=models.Q(trigger_kind__in=("single_report", "zone_cluster")),
                name="chk_alert_trigger_kind",
            ),
            models.CheckConstraint(
                condition=models.Q(trigger_kind="zone_cluster")
                | models.Q(focus_center__isnull=False),
                name="chk_alert_focus_center",
            ),
            models.CheckConstraint(
                condition=~models.Q(trigger_kind="zone_cluster")
                | models.Q(species__isnull=False),
                name="chk_alert_cluster_species",
            ),
            models.CheckConstraint(condition=models.Q(confidence__in=("normal", "reduced")),
                                   name="chk_alert_confidence"),
            models.CheckConstraint(
                condition=models.Q(status__in=("open", "monitoring", "closed", "cancelled")),
                name="chk_alert_status",
            ),
        ]


class AlertReport(models.Model):
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE)
    report = models.ForeignKey("health.HealthReport", on_delete=models.PROTECT,
                               related_name="+")
    pk = models.CompositePrimaryKey("alert_id", "report_id")

    class Meta:
        db_table = "alert_report"


class AlertReview(EventModel):
    class Decision(models.TextChoices):
        CONFIRM = "confirm", "Confirmer"
        DISMISS = "dismiss", "Infirmer"
        NEED_INFO = "need_info", "Demander des informations"

    alert = models.ForeignKey(Alert, on_delete=models.PROTECT, related_name="reviews")
    decision = models.CharField(max_length=10, choices=Decision.choices)
    habilitation = models.ForeignKey("accounts.Habilitation", on_delete=models.PROTECT,
                                     related_name="+")
    note = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "alert_review"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(decision__in=("confirm", "dismiss", "need_info")),
                name="chk_alert_review_decision",
            )
        ]


class AlertExposure(UUIDModel):
    class Status(models.TextChoices):
        EXPOSED = "exposed", "Contact possible"
        EXCLUDED_NEGATIVE = "excluded_negative", "Écarté"
        MONITORING = "monitoring", "Surveillance"
        CLEARED = "cleared", "Levé"

    alert = models.ForeignKey(Alert, on_delete=models.PROTECT, related_name="exposures")
    run_id = models.UUIDField()
    center = models.ForeignKey("identity.Center", on_delete=models.PROTECT, related_name="+")
    unit = models.ForeignKey("identity.TrackedUnit", null=True, blank=True,
                             on_delete=models.PROTECT, related_name="+")
    exposure_status = models.CharField(max_length=18, choices=Status.choices)
    depth = models.SmallIntegerField()
    last_contact_at = models.DateTimeField(null=True, blank=True)
    computed_at = models.DateTimeField()

    class Meta:
        db_table = "alert_exposure"
        indexes = [
            models.Index(fields=("alert", "run_id"), name="idx_alert_exposure_run"),
            models.Index(fields=("center",), name="idx_alert_exposure_center"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    exposure_status__in=("exposed", "excluded_negative", "monitoring", "cleared")
                ),
                name="chk_alert_exposure_status",
            ),
            models.CheckConstraint(condition=models.Q(depth__gte=0),
                                   name="chk_alert_exposure_depth"),
            models.UniqueConstraint(
                fields=("alert", "run_id", "center", "unit"), nulls_distinct=False,
                name="uniq_alert_exposure_run_center_unit",
            ),
        ]


class AlertExposureStep(UUIDModel):
    exposure = models.ForeignKey(AlertExposure, on_delete=models.PROTECT, related_name="steps")
    step_no = models.SmallIntegerField()
    movement = models.ForeignKey("traceability.Movement", null=True, blank=True,
                                 on_delete=models.PROTECT, related_name="+")
    from_center = models.ForeignKey("identity.Center", on_delete=models.PROTECT,
                                    related_name="+")
    to_center = models.ForeignKey("identity.Center", on_delete=models.PROTECT,
                                  related_name="+")
    unit = models.ForeignKey("identity.TrackedUnit", null=True, blank=True,
                             on_delete=models.PROTECT, related_name="+")
    occurred_at = models.DateTimeField()
    explanation_code = models.CharField(max_length=30)

    class Meta:
        db_table = "alert_exposure_step"
        constraints = [
            models.CheckConstraint(condition=models.Q(step_no__gte=1),
                                   name="chk_alert_exposure_step_no"),
            models.UniqueConstraint(fields=("exposure", "step_no"),
                                    name="uniq_alert_exposure_step"),
        ]


ALERT_EVENT_TYPES = ("opened", "level_changed", "recomputed", "notified", "vets_notified",
                     "escalated", "reviewed", "reopened", "closed", "cancelled")


class AlertEvent(EventModel):
    alert = models.ForeignKey(Alert, on_delete=models.PROTECT, related_name="events")
    event_type = models.CharField(max_length=16, choices=[(t, t) for t in ALERT_EVENT_TYPES])
    payload = models.JSONField(default=dict)

    class Meta:
        db_table = "alert_event"
        constraints = [
            models.CheckConstraint(condition=models.Q(event_type__in=ALERT_EVENT_TYPES),
                                   name="chk_alert_event_type"),
        ]


class Investigation(StateModel):
    """Enquête de terrain (P2)."""

    alert = models.ForeignKey(Alert, on_delete=models.PROTECT, related_name="+")
    center = models.ForeignKey("identity.Center", on_delete=models.PROTECT, related_name="+")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                    related_name="+")
    status = models.CharField(max_length=10, default="open")
    findings = models.TextField(null=True, blank=True)
    opened_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "investigation"
        constraints = [
            models.CheckConstraint(condition=models.Q(status__in=("open", "done", "cancelled")),
                                   name="chk_investigation_status"),
        ]


class Quarantine(StateModel):
    """Restriction de mouvement (P2). BAOBIA suit la mesure sans l'imposer."""

    alert = models.ForeignKey(Alert, on_delete=models.PROTECT, related_name="+")
    center = models.ForeignKey("identity.Center", null=True, blank=True,
                               on_delete=models.PROTECT, related_name="+")
    unit = models.ForeignKey("identity.TrackedUnit", null=True, blank=True,
                             on_delete=models.PROTECT, related_name="+")
    starts_on = models.DateField()
    ends_on = models.DateField(null=True, blank=True)
    ordered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                   related_name="+")
    habilitation = models.ForeignKey("accounts.Habilitation", on_delete=models.PROTECT,
                                     related_name="+")

    class Meta:
        db_table = "quarantine"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(center__isnull=False) | models.Q(unit__isnull=False),
                name="chk_quarantine_target",
            ),
        ]
