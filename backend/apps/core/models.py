import uuid

from django.conf import settings
from django.db import models


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class StateModel(UUIDModel):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_simulated = models.BooleanField(default=False)

    class Meta:
        abstract = True


class EventFields(UUIDModel):
    occurred_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    device = models.ForeignKey(
        "accounts.Device", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    is_simulated = models.BooleanField(default=False)

    class Meta:
        abstract = True


class EventModel(EventFields):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise RuntimeError("Un événement ne se modifie pas.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Un événement ne se supprime pas.")


class DeclarationModel(EventFields):
    class Meta:
        abstract = True


class CorrectableMixin(models.Model):
    supersedes = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )

    class Meta:
        abstract = True


class PositionMixin(models.Model):
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    position_accuracy_m = models.DecimalField(
        max_digits=7, decimal_places=1, null=True, blank=True
    )
    position_source = models.CharField(
        max_length=8,
        choices=(
            ("gps", "GPS"),
            ("network", "Network"),
            ("manual", "Manual"),
            ("none", "None"),
        ),
        default="none",
    )

    class Meta:
        abstract = True


class Species(UUIDModel):
    code = models.CharField(max_length=20, unique=True)
    label_fr = models.CharField(max_length=60)
    tracking_mode = models.CharField(max_length=10)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "species"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(tracking_mode__in=("animal", "lot", "both")),
                name="chk_species_tracking_mode",
            )
        ]
