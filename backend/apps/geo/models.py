from django.db import models

from apps.core.models import UUIDModel


class Zone(UUIDModel):
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    level = models.SmallIntegerField()
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        db_table = "zone"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(level__gte=0) & models.Q(level__lte=6),
                name="chk_zone_level",
            )
        ]
