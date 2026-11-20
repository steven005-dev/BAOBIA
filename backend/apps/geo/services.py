"""Fonctions publiques du module geo (responsable : Yéo).

zone_stat est un cache : seule cette fonction l'écrit. Le calcul des états (qui lit
alertes et signalements) est fait par alerts.services.recompute_zone_stats, car geo
ne dépend d'aucun module métier (core <- geo <- ... <- alerts).
"""

import json
from decimal import Decimal
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from .models import Zone, ZoneStat

CI_ZONES_FILE = Path(__file__).resolve().parent / "data" / "ci_zones.json"


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


@transaction.atomic
def load_ci_zones(country):
    """Crée ou met à jour les 14 districts (niveau 1) et les 33 régions (niveau 2 : 31 régions
    et les 2 districts autonomes) de Côte d'Ivoire sous la zone pays `country`.
    Tracés : geoBoundaries (CC BY 4.0) ; le front a les mêmes codes (ci-zones.json).
    Idempotent. Renvoie {code: Zone}."""
    data = json.loads(CI_ZONES_FILE.read_text(encoding="utf-8"))
    zones = {}
    for item in sorted(data["zones"], key=lambda z: z["level"]):
        parent = zones[item["parent"]] if item["parent"] else country
        zones[item["code"]], _ = Zone.objects.update_or_create(
            code=item["code"],
            defaults={"name": item["name"], "level": item["level"], "parent": parent,
                      "latitude": Decimal(str(item["lat"])), "longitude": Decimal(str(item["lon"]))},
        )
    return zones
