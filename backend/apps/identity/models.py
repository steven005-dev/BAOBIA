import re

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

from apps.core.models import (
    CorrectableMixin,
    DeclarationModel,
    EventModel,
    PositionMixin,
    StateModel,
    UUIDModel,
)


class Center(StateModel):
    name = models.CharField(max_length=160)
    organization = models.ForeignKey(
        "accounts.Organization", null=True, blank=True, on_delete=models.PROTECT
    )
    zone = models.ForeignKey("geo.Zone", on_delete=models.PROTECT)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_accuracy_m = models.DecimalField(
        max_digits=7, decimal_places=1, null=True, blank=True
    )
    location_source = models.CharField(max_length=10, default="none")
    center_type = models.CharField(max_length=15)
    status = models.CharField(max_length=10, default="active")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        db_table = "center"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(location_source__in=("gps", "manual", "none")),
                name="chk_center_location_source",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    center_type__in=("farm", "market", "slaughterhouse", "checkpoint", "other")
                ),
                name="chk_center_type",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=("active", "closed")),
                name="chk_center_status",
            ),
        ]


class CenterMember(UUIDModel):
    center = models.ForeignKey("identity.Center", on_delete=models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    member_role = models.CharField(max_length=10)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "center_member"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(member_role__in=("holder", "co_holder", "worker")),
                name="chk_center_member_role",
            ),
            models.CheckConstraint(
                condition=models.Q(ends_at__isnull=True)
                | models.Q(ends_at__gt=models.F("starts_at")),
                name="chk_center_member_dates",
            ),
            models.UniqueConstraint(
                fields=("center",),
                condition=models.Q(member_role="holder", ends_at__isnull=True),
                name="uniq_center_active_holder",
            ),
            models.UniqueConstraint(
                fields=("center", "user"),
                condition=models.Q(ends_at__isnull=True),
                name="uniq_center_active_member",
            ),
        ]


class CenterSpecies(models.Model):
    center = models.ForeignKey("identity.Center", on_delete=models.CASCADE)
    species = models.ForeignKey("core.Species", on_delete=models.PROTECT)
    pk = models.CompositePrimaryKey("center_id", "species_id")

    class Meta:
        db_table = "center_species"


class TrackedUnit(StateModel):
    kind = models.CharField(max_length=6)
    species = models.ForeignKey("core.Species", on_delete=models.PROTECT)
    current_center = models.ForeignKey(
        "identity.Center", null=True, blank=True, on_delete=models.PROTECT, editable=False
    )
    life_status = models.CharField(max_length=10, default="active", editable=False)
    local_name = models.CharField(max_length=60, null=True, blank=True)
    merged_into = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="merged_units"
    )
    origin_unit = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="derived_units"
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    device = models.ForeignKey(
        "accounts.Device", null=True, blank=True, on_delete=models.PROTECT
    )

    class Meta:
        db_table = "tracked_unit"
        indexes = [models.Index(fields=("current_center",), name="idx_tracked_unit_center")]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(kind__in=("animal", "lot")),
                name="chk_tracked_unit_kind",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    life_status__in=("active", "dead", "slaughtered", "missing", "closed")
                ),
                name="chk_tracked_unit_life_status",
            ),
        ]


class Animal(models.Model):
    unit = models.OneToOneField(
        TrackedUnit, primary_key=True, on_delete=models.CASCADE, db_column="unit_id"
    )
    sex = models.CharField(max_length=7, default="unknown")
    birth_date = models.DateField(null=True, blank=True)
    birth_date_precision = models.CharField(max_length=9, null=True, blank=True)
    breed = models.CharField(max_length=60, null=True, blank=True)
    marks = models.TextField(null=True, blank=True)
    mother = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="offspring"
    )

    class Meta:
        db_table = "animal"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(sex__in=("male", "female", "unknown")),
                name="chk_animal_sex",
            ),
            models.CheckConstraint(
                condition=models.Q(birth_date_precision__isnull=True)
                | models.Q(birth_date_precision__in=("day", "month", "year", "estimated")),
                name="chk_animal_birth_precision",
            ),
        ]


class Lot(models.Model):
    unit = models.OneToOneField(
        TrackedUnit, primary_key=True, on_delete=models.CASCADE, db_column="unit_id"
    )
    current_size = models.PositiveIntegerField(editable=False)
    description = models.CharField(max_length=120, null=True, blank=True)

    class Meta:
        db_table = "lot"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(current_size__gt=0), name="chk_lot_current_size"
            )
        ]


class LabelBatch(UUIDModel):
    quantity = models.PositiveIntegerField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=160, null=True, blank=True)

    class Meta:
        db_table = "label_batch"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0), name="chk_label_batch_quantity"
            )
        ]


class Label(UUIDModel):
    batch = models.ForeignKey(LabelBatch, on_delete=models.PROTECT)
    short_code = models.CharField(
        max_length=9,
        unique=True,
        validators=[RegexValidator(re.compile(r"^[2-9A-HJ-NP-Z]{9}$"))],
    )
    kind = models.CharField(max_length=10, default="qr")
    status = models.CharField(max_length=12, default="printed")
    issued_to_center = models.ForeignKey(
        "identity.Center", null=True, blank=True, on_delete=models.PROTECT
    )

    class Meta:
        db_table = "label"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(kind__in=("qr", "ear_tag", "other")),
                name="chk_label_kind",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=("printed", "issued", "active", "deactivated", "lost")),
                name="chk_label_status",
            ),
            models.CheckConstraint(
                condition=models.Q(short_code__regex=r"^[2-9A-HJ-NP-Z]{9}$"),
                name="chk_label_short_code",
            ),
        ]


class IdentitySupport(UUIDModel):
    unit = models.ForeignKey(TrackedUnit, on_delete=models.PROTECT)
    support_type = models.CharField(max_length=12)
    label = models.ForeignKey(Label, null=True, blank=True, on_delete=models.PROTECT)
    mark_text = models.CharField(max_length=60, null=True, blank=True)
    bound_at = models.DateTimeField()
    bound_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    unbound_at = models.DateTimeField(null=True, blank=True)
    unbound_reason = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        db_table = "identity_support"
        indexes = [
            models.Index(
                fields=("unit",), name="idx_identity_support_active",
                condition=models.Q(unbound_at__isnull=True),
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(support_type__in=("qr_label", "visible_mark", "rfid_future")),
                name="chk_identity_support_type",
            ),
            models.CheckConstraint(
                condition=models.Q(support_type="qr_label") & models.Q(label__isnull=False)
                | ~models.Q(support_type="qr_label"),
                name="chk_identity_support_qr_label",
            ),
            models.CheckConstraint(
                condition=models.Q(unbound_reason__isnull=True)
                | models.Q(unbound_reason__in=("lost", "damaged", "replaced", "error")),
                name="chk_identity_support_unbound_reason",
            ),
            models.UniqueConstraint(
                fields=("label",), condition=models.Q(unbound_at__isnull=True),
                nulls_distinct=False, name="uniq_identity_support_active_label",
            ),
            models.UniqueConstraint(
                fields=("unit",), condition=models.Q(support_type="qr_label", unbound_at__isnull=True),
                name="uniq_identity_support_active_qr",
            ),
        ]


class IdentityVerification(PositionMixin, EventModel):
    unit = models.ForeignKey(TrackedUnit, on_delete=models.PROTECT)
    label = models.ForeignKey(Label, null=True, blank=True, on_delete=models.PROTECT)
    method = models.CharField(max_length=12)
    result = models.CharField(max_length=10)

    class Meta:
        db_table = "identity_verification"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(method__in=("scan", "manual_code", "photo_compare")),
                name="chk_identity_verification_method",
            ),
            models.CheckConstraint(
                condition=models.Q(result__in=("confirmed", "mismatch", "unreadable")),
                name="chk_identity_verification_result",
            ),
        ]


class OwnershipClaim(DeclarationModel, CorrectableMixin):
    unit = models.ForeignKey(TrackedUnit, on_delete=models.PROTECT)
    party_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    role = models.CharField(max_length=10)
    status = models.CharField(max_length=10, default="declared")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ownership_claim"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role__in=("owner", "holder")),
                name="chk_ownership_claim_role",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=("declared", "contested", "confirmed", "superseded")),
                name="chk_ownership_claim_status",
            ),
            models.UniqueConstraint(
                fields=("supersedes",), condition=models.Q(supersedes__isnull=False),
                name="uniq_ownership_claim_supersedes",
            ),
        ]


class Attachment(UUIDModel):
    storage_key = models.CharField(max_length=255, unique=True)
    mime_type = models.CharField(max_length=80)
    size_bytes = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "attachment"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(size_bytes__gt=0), name="chk_attachment_size"
            )
        ]


class SubjectPhoto(UUIDModel):
    unit = models.ForeignKey(TrackedUnit, on_delete=models.PROTECT)
    attachment = models.ForeignKey(Attachment, on_delete=models.PROTECT)
    purpose = models.CharField(max_length=12)
    taken_at = models.DateTimeField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        db_table = "subject_photo"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(purpose__in=("registration", "health", "verification")),
                name="chk_subject_photo_purpose",
            )
        ]


class MandateCenter(models.Model):
    mandate = models.ForeignKey("accounts.Mandate", on_delete=models.CASCADE)
    center = models.ForeignKey(Center, on_delete=models.CASCADE)
    pk = models.CompositePrimaryKey("mandate_id", "center_id")

    class Meta:
        db_table = "mandate_center"
