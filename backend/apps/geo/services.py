"""Fonctions publiques du module geo (responsable : Yéo).

zone_stat est un cache : seule cette fonction l'écrit. Le calcul des états (qui lit
alertes et signalements) est fait par alerts.services.recompute_zone_stats, car geo
ne dépend d'aucun module métier (core <- geo <- ... <- alerts).
"""

from django.utils import timezone

from .models import ZoneStat


def save_zone_stat(*, zone_id, species_id, state, centers_count, animals_count, is_masked,
                   computed_at=None):
    """Crée ou remplace la ligne courante (zone, espèce). species_id None = toutes espèces."""
    values = {
        "state": "unknown" if is_masked else state,
        "centers_count": centers_count,
        "animals_count": animals_count,
        "is_masked": is_masked,
        "computed_at": computed_at or timezone.now(),
    }
    stat, _ = ZoneStat.objects.update_or_create(
        zone_id=zone_id, species_id=species_id, defaults=values
    )
    return stat
