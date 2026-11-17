"""Modèles du module health (responsable : Yéo).

Conformes à docs/BAOBIA_DB_SPEC.md, section 6, application `health`.
- Catalogues : Disease, Symptom (+ liaisons espèces).
- Carnet sanitaire : HealthEvent (événement en ajout seul, corrigeable).
- Signalement : HealthReport (déclaration ; `status` est un cache écrit par
  health.services), ses symptômes, ses unités, ses photos.
- Évaluation vétérinaire : HealthReportReview (événement en ajout seul).
"""

from django.db import models

from apps.core.models import (
    CorrectableMixin,
    DeclarationModel,
    EventModel,
    PositionMixin,
    UUIDModel,
)

# ---------------------------------------------------------------------------
# Catalogues
# ---------------------------------------------------------------------------


class Disease(UUIDModel):
    code = models.CharField(max_length=30, unique=True)
    label_fr = models.CharField(max_length=100)
    is_notifiable = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    species = models.ManyToManyField(
        "core.Species", through="DiseaseSpecies", related_name="+", blank=True
    )

    class Meta:
        db_table = "disease"

    def __str__(self):
        return self.label_fr


class DiseaseSpecies(models.Model):
    disease = models.ForeignKey(Disease, on_delete=models.CASCADE)
    species = models.ForeignKey("core.Species", on_delete=models.PROTECT, related_name="+")
    pk = models.CompositePrimaryKey("disease_id", "species_id")

    class Meta:
        db_table = "disease_species"


class Symptom(UUIDModel):
    code = models.CharField(max_length=30, unique=True)
    label_fr = models.CharField(max_length=100)
    icon = models.CharField(max_length=40, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    species = models.ManyToManyField(
        "core.Species", through="SymptomSpecies", related_name="+", blank=True
    )

    class Meta:
        db_table = "symptom"

    def __str__(self):
        return self.label_fr


class SymptomSpecies(models.Model):
    symptom = models.ForeignKey(Symptom, on_delete=models.CASCADE)
    species = models.ForeignKey("core.Species", on_delete=models.PROTECT, related_name="+")
    pk = models.CompositePrimaryKey("symptom_id", "species_id")

    class Meta:
        db_table = "symptom_species"


# ---------------------------------------------------------------------------
# Carnet sanitaire
# ---------------------------------------------------------------------------


class HealthEvent(EventModel, CorrectableMixin):
    """Vaccination, traitement, examen d'une unité. Ajout seul ; une correction
    est une nouvelle ligne qui pointe l'ancienne (`supersedes`)."""

    class EventType(models.TextChoices):
        VACCINATION = "vaccination", "Vaccination"
        TREATMENT = "treatment", "Traitement"
        EXAMINATION = "examination", "Examen"
        LAB_RESULT = "lab_result", "Résultat d'analyse"  # P2

    unit = models.ForeignKey("identity.TrackedUnit", on_delete=models.PROTECT, related_name="+")
    event_type = models.CharField(max_length=14, choices=EventType.choices)
    disease = models.ForeignKey(
        Disease, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    product = models.CharField(max_length=80, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "health_event"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    event_type__in=("vaccination", "treatment", "examination", "lab_result")
                ),
                name="chk_health_event_type",
            ),
            models.UniqueConstraint(
                fields=("supersedes",),
                condition=models.Q(supersedes__isnull=False),
                name="uniq_health_event_supersedes",
            ),
        ]


# ---------------------------------------------------------------------------
# Signalement
# ---------------------------------------------------------------------------


class HealthReport(DeclarationModel, PositionMixin):
    """Signalement d'un cas suspect par un éleveur ou un agent.

    `occurred_at` = date d'observation (appareil) ; `created_at` = réception serveur.
    `status` est un cache de health_report_review : écrit seulement par health.services.
    Un signalement n'a aucun effet visible hors des professionnels avant examen (RG-14).
    """

    class Kind(models.TextChoices):
        SUSPICION = "suspicion", "Cas suspect"
        DEATH = "death", "Mort"
        ABNORMAL_MORTALITY = "abnormal_mortality", "Morts nombreuses"

    class Severity(models.TextChoices):
        LOW = "low", "Faible"
        MEDIUM = "medium", "Moyenne"
        HIGH = "high", "Forte"

    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Reçu"
        UNDER_REVIEW = "under_review", "En examen"
        VALIDATED = "validated", "Validé"
        REJECTED = "rejected", "Refusé"
        CLOSED = "closed", "Clôturé"

    center = models.ForeignKey("identity.Center", on_delete=models.PROTECT, related_name="+")
    report_kind = models.CharField(max_length=18, choices=Kind.choices)
    affected_count = models.IntegerField(default=1)
    self_severity = models.CharField(max_length=6, choices=Severity.choices)
    note = models.CharField(max_length=500, null=True, blank=True)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.SUBMITTED, editable=False
    )
    symptoms = models.ManyToManyField(
        Symptom, through="HealthReportSymptom", related_name="+", blank=True
    )

    class Meta:
        db_table = "health_report"
        indexes = [
            models.Index(fields=("center", "-occurred_at"), name="idx_health_report_center"),
            models.Index(fields=("status",), name="idx_health_report_status"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    report_kind__in=("suspicion", "death", "abnormal_mortality")
                ),
                name="chk_health_report_kind",
            ),
            models.CheckConstraint(
                condition=models.Q(affected_count__gt=0),
                name="chk_health_report_affected_count",
            ),
            models.CheckConstraint(
                condition=models.Q(self_severity__in=("low", "medium", "high")),
                name="chk_health_report_severity",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=("submitted", "under_review", "validated", "rejected", "closed")
                ),
                name="chk_health_report_status",
            ),
            models.CheckConstraint(
                condition=models.Q(position_source__in=("gps", "network", "manual", "none")),
                name="chk_health_report_position_source",
            ),
        ]


class HealthReportSymptom(models.Model):
    report = models.ForeignKey(HealthReport, on_delete=models.CASCADE)
    symptom = models.ForeignKey(Symptom, on_delete=models.PROTECT)
    pk = models.CompositePrimaryKey("report_id", "symptom_id")

    class Meta:
        db_table = "health_report_symptom"


class HealthReportSubject(models.Model):
    class Condition(models.TextChoices):
        SICK = "sick", "Malade"
        DEAD = "dead", "Mort"
        SUSPECT = "suspect", "Suspect"
        CONTACT = "contact", "Contact"

    report = models.ForeignKey(HealthReport, on_delete=models.CASCADE, related_name="subjects")
    unit = models.ForeignKey("identity.TrackedUnit", on_delete=models.PROTECT, related_name="+")
    pk = models.CompositePrimaryKey("report_id", "unit_id")
    condition = models.CharField(max_length=10, choices=Condition.choices)
    notes = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        db_table = "health_report_subject"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(condition__in=("sick", "dead", "suspect", "contact")),
                name="chk_health_report_subject_condition",
            )
        ]


class HealthReportAttachment(models.Model):
    report = models.ForeignKey(HealthReport, on_delete=models.CASCADE)
    attachment = models.ForeignKey("identity.Attachment", on_delete=models.PROTECT, related_name="+")
    pk = models.CompositePrimaryKey("report_id", "attachment_id")

    class Meta:
        db_table = "health_report_attachment"


class HealthReportReview(EventModel):
    """Évaluation d'un signalement par un vétérinaire habilité. Ajout seul.

    `habilitation` = preuve d'habilitation valide au moment de la décision
    (vérifiée par health.services, via accounts.services.get_valid_habilitation).
    """

    class Decision(models.TextChoices):
        REQUEST_INFO = "request_info", "Demander des informations"
        RETAIN_SUSPICION = "retain_suspicion", "Garder la suspicion"
        RAISE_LEVEL2 = "raise_level2", "Passer au niveau 2"
        VALIDATE_LEVEL3 = "validate_level3", "Valider (niveau 3)"
        DISMISS = "dismiss", "Refuser"
        CLOSE = "close", "Clôturer"

    report = models.ForeignKey(HealthReport, on_delete=models.PROTECT, related_name="reviews")
    decision = models.CharField(max_length=20, choices=Decision.choices)
    disease = models.ForeignKey(
        Disease, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    habilitation = models.ForeignKey(
        "accounts.Habilitation", on_delete=models.PROTECT, related_name="+"
    )
    note = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "health_report_review"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    decision__in=(
                        "request_info",
                        "retain_suspicion",
                        "raise_level2",
                        "validate_level3",
                        "dismiss",
                        "close",
                    )
                ),
                name="chk_health_report_review_decision",
            )
        ]
