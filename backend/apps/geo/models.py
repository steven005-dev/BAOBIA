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

    def __str__(self):
        return f"{self.code} - {self.name}"


class ZoneStat(UUIDModel):
    """État courant d'une zone sur la carte (cache recalculé par geo.services).

    Une seule ligne par (zone, espèce) ; species NULL = toutes espèces.
    Aucune colonne n'est écrite ailleurs que dans geo.services.
    """

    class State(models.TextChoices):
        NORMAL = "normal", "Normal"
        WATCH = "watch", "À surveiller"
        EXPOSURE = "exposure", "Contact possible"
        ALERT = "alert", "Alerte validée"
        UNKNOWN = "unknown", "Pas assez de données"

    zone = models.ForeignKey(Zone, on_delete=models.PROTECT, related_name="stats")
    species = models.ForeignKey(
        "core.Species", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    state = models.CharField(max_length=10, choices=State.choices, editable=False)
    centers_count = models.IntegerField(default=0, editable=False)
    animals_count = models.IntegerField(default=0, editable=False)
    is_masked = models.BooleanField(default=False, editable=False)
    computed_at = models.DateTimeField(editable=False)

    class Meta:
        db_table = "zone_stat"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(state__in=("normal", "watch", "exposure", "alert", "unknown")),
                name="chk_zone_stat_state",
            ),
            models.CheckConstraint(
                condition=models.Q(centers_count__gte=0) & models.Q(animals_count__gte=0),
                name="chk_zone_stat_counts",
            ),
            models.UniqueConstraint(
                fields=("zone", "species"),
                nulls_distinct=False,
                name="uniq_zone_stat_zone_species",
            ),
        ]
