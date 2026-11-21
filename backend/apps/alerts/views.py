"""Routes alerts : alertes (espace vétérinaire) et carte par zones.

- Les alertes et la chaîne d'exposition ne sont visibles que des vétérinaires et
  autorités de la zone (RG-13) ; chaque consultation est journalisée (TR-03).
  Les éleveurs ne reçoivent que des messages neutres (module notifications).
- La carte ne donne aucun nom ni position d'élevage, sauf ceux de l'utilisateur (CA-04).
"""

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasRole
from apps.accounts.serializers import ErrorSerializer
from apps.audit.services import record_event
from apps.geo.models import ZoneStat
from apps.identity.models import Center
from apps.identity.services import accessible_centers, active_label
from apps.traceability.models import Movement
from apps.traceability.services import CONFIDENCE_BY_STATUS, movement_confidence

from . import services
from .models import Alert

TAG_ALERTS = "Alertes"
TAG_MAP = "Carte"
PROFESSIONALS = HasRole("veterinarian", "authority")


def _ref(obj, label="label_fr"):
    return {"code": obj.code, "label_fr": getattr(obj, label)} if obj else None


def _alert_summary(alert):
    exposures = services.current_exposures(alert) if alert.current_run_id else None
    return {
        "id": alert.id,
        "level": alert.level,
        "status": alert.status,
        "trigger_kind": alert.trigger_kind,
        "confidence": alert.confidence,
        "disease": _ref(alert.disease),
        "species": _ref(alert.species),
        "zone": {"id": alert.zone_id, "name": alert.zone.name},
        "focus_center": ({"id": alert.focus_center_id, "name": alert.focus_center.name}
                         if alert.focus_center_id else None),
        "opened_at": alert.opened_at,
        "validated_at": alert.validated_at,
        "validated_by": alert.validated_by.full_name if alert.validated_by_id else None,
        "exposed_count": exposures.filter(exposure_status="exposed").count() if exposures else 0,
        "excluded_count": (exposures.filter(exposure_status="excluded_negative").count()
                           if exposures else 0),
        "is_simulated": alert.is_simulated,
    }


def _alert_queryset():
    return Alert.objects.select_related("disease", "species", "zone", "focus_center",
                                        "validated_by", "rule")


class AlertListView(APIView):
    permission_classes = [PROFESSIONALS]

    @extend_schema(tags=[TAG_ALERTS], operation_id="alerts_list", summary="Alertes de mes zones (vétérinaire, autorité)",
                   parameters=[OpenApiParameter("status", str, description="open, monitoring, "
                                                "closed, cancelled")],
                   responses={200: dict, 403: ErrorSerializer})
    def get(self, request):
        alerts = _alert_queryset().filter(
            pk__in=services.visible_alerts(request.user).values("pk"))
        if request.query_params.get("status"):
            alerts = alerts.filter(status=request.query_params["status"])
        return Response([_alert_summary(a) for a in alerts.order_by("-level", "-opened_at")[:200]])


class AlertDetailView(APIView):
    permission_classes = [PROFESSIONALS]

    @extend_schema(
        tags=[TAG_ALERTS],
        operation_id="alerts_detail",
        summary="Alerte expliquée : règle, signalements, élevages exposés et écartés",
        description="Chaque élevage exposé ou écarté porte son chemin (mouvements, dates, "
                    "raison). « Exposé » signifie contact possible, jamais contamination.",
        responses={200: dict, 403: ErrorSerializer, 404: ErrorSerializer},
    )
    def get(self, request, alert_id):
        alert = _alert_queryset().filter(pk=alert_id).first()
        if alert is None or not services.is_professional_for_alert(request.user, alert):
            raise NotFound("Alerte introuvable.")
        rule = alert.rule
        data = _alert_summary(alert)
        data["rule"] = {
            "version": rule.version, "lookback_days": rule.lookback_days,
            "lookforward_days": rule.lookforward_days, "max_depth": rule.max_depth,
            "include_unconfirmed": rule.include_unconfirmed,
            "experimental": True,  # valeurs de démonstration, à valider par un vétérinaire
        }
        data["reports"] = [
            {"id": r.id, "center_id": r.center_id, "occurred_at": r.occurred_at,
             "affected_count": r.affected_count, "status": r.status}
            for r in alert.reports.all().order_by("occurred_at")
        ]
        exposures = (services.current_exposures(alert).select_related("center")
                     .prefetch_related("steps__from_center", "steps__to_center",
                                       "steps__movement")
                     .order_by("exposure_status", "depth")) if alert.current_run_id else []
        data["exposures"] = [
            {
                "center": {"id": e.center_id, "name": e.center.name},
                "status": e.exposure_status,
                "depth": e.depth,
                "last_contact_at": e.last_contact_at,
                "path": [
                    {"step": s.step_no, "movement_id": s.movement_id,
                     "from": s.from_center.name, "to": s.to_center.name,
                     "occurred_at": s.occurred_at, "reason": s.explanation_code,
                     # declared = transfert déclaré d'un seul côté (vétérinaire seulement)
                     "movement_status": s.movement.status}
                    for s in sorted(e.steps.all(), key=lambda s: s.step_no)
                ],
            }
            for e in exposures
        ]
        data["events"] = [
            {"type": ev.event_type, "at": ev.occurred_at, "payload": ev.payload}
            for ev in alert.events.order_by("occurred_at")
        ]
        record_event("alert.view", actor_user=request.user, entity_table="alert",
                     entity_id=alert.pk)
        return Response(data)


def _counts_hidden(stats):
    """Zones dont les effectifs ne sont pas donnés : les zones masquées ET toutes leurs zones
    mères (district, pays). Sinon, l'effectif d'une région masquée se retrouverait par
    soustraction (effectif du district moins celui des régions visibles)."""
    from apps.geo.models import Zone

    parents = dict(Zone.objects.values_list("id", "parent_id"))
    hidden = set()
    for s in stats:
        zone_id = s.zone_id if s.is_masked else None
        while zone_id is not None and zone_id not in hidden:
            hidden.add(zone_id)
            zone_id = parents.get(zone_id)
    return hidden


class MapZonesView(APIView):
    @extend_schema(
        tags=[TAG_MAP],
        summary="Carte par zones",
        description=(
            "États : normal, watch (à surveiller), exposure (contact possible), alert (alerte "
            "validée), unknown (pas assez de données). Une zone masquée ne donne aucun "
            "effectif. Élevages : ceux de l'utilisateur (my_centers) ; pour un vétérinaire ou "
            "une autorité, aussi les points des élevages de ses zones (points : position et "
            "type seulement, ni nom ni identifiant)."
        ),
        parameters=[OpenApiParameter("species", str, description="Code d'espèce ; vide = "
                                                                 "toutes espèces.")],
        responses={200: dict},
    )
    def get(self, request):
        species_code = request.query_params.get("species")
        stats = ZoneStat.objects.select_related("zone")
        stats = stats.filter(species__code=species_code) if species_code else \
            stats.filter(species__isnull=True)
        stats = list(stats.order_by("zone__name"))
        hidden = _counts_hidden(stats)
        zones = [
            {
                "zone": {"id": s.zone_id, "code": s.zone.code, "name": s.zone.name,
                         "level": s.zone.level, "parent_id": s.zone.parent_id,
                         "latitude": s.zone.latitude, "longitude": s.zone.longitude},
                "state": s.state,
                "is_masked": s.is_masked,
                "centers_count": None if s.zone_id in hidden else s.centers_count,
                "animals_count": None if s.zone_id in hidden else s.animals_count,
                "computed_at": s.computed_at,
            }
            for s in stats
        ]
        mine = Center.objects.filter(pk__in=[c["id"] for c in accessible_centers(request.user)])
        covered = services._covered_zone_ids(request.user)
        points = Center.objects.filter(
            zone_id__in=covered, status="active", latitude__isnull=False, longitude__isnull=False
        ).values("latitude", "longitude", "zone_id", "center_type") if covered else []
        return Response({
            "zones": zones,
            "my_centers": [
                {"id": c.id, "name": c.name, "zone_id": c.zone_id,
                 "latitude": c.latitude, "longitude": c.longitude}
                for c in mine
            ],
            "points": [
                {"latitude": p["latitude"], "longitude": p["longitude"], "zone_id": p["zone_id"],
                 "type": p["center_type"]}
                for p in points
            ],
        })


# Confiance d'un mouvement : règle du module traceability (Romuald, R1), pas une copie ici.
FLOW_DAYS = (7, 30, 90, 365)


def _flow_place(center):
    return {"name": center.name, "zone": center.zone.name, "type": center.center_type,
            "latitude": center.latitude, "longitude": center.longitude}


class MapFlowsView(APIView):
    """Flux des animaux pour la carte : vétérinaire et autorité seulement, sur leurs zones."""

    permission_classes = [HasRole("veterinarian", "authority")]

    @extend_schema(
        tags=[TAG_MAP],
        summary="Flux des animaux (vétérinaire, autorité)",
        description=(
            "Mouvements entre deux élevages dont l'un est dans une zone couverte par "
            "l'utilisateur, sur les `days` derniers jours (7, 30, 90 ou 365 ; 30 par défaut). "
            "Pour chacun : origine, destination, date, confiance (confirmed = confirmé des deux côtés, "
            "one_side = déclaré d'un seul côté, disputed = contesté) et les animaux ou lots "
            "(espèce, code d'étiquette). Annulés et expirés exclus."
        ),
        parameters=[OpenApiParameter("days", int), OpenApiParameter("species", str)],
        responses={200: dict},
    )
    def get(self, request):
        try:
            days = int(request.query_params.get("days", 30))
        except ValueError:
            days = 30
        days = days if days in FLOW_DAYS else 30
        covered = services._covered_zone_ids(request.user)
        movements = (
            Movement.objects.filter(to_center__isnull=False, status__in=list(CONFIDENCE_BY_STATUS),
                                    occurred_at__gte=timezone.now() - timedelta(days=days))
            .filter(Q(from_center__zone_id__in=covered) | Q(to_center__zone_id__in=covered))
            .select_related("from_center__zone", "to_center__zone")
            .prefetch_related("items__unit__species", "items__unit__animal")
            .order_by("-occurred_at")[:300]
        )
        species = request.query_params.get("species")
        flows = []
        for m in movements:
            animals = []
            for item in m.items.all():
                unit = item.unit
                if species and unit.species.code != species:
                    continue
                label = active_label(unit)
                animal = getattr(unit, "animal", None) if unit.kind == "animal" else None
                animals.append({
                    "kind": unit.kind, "species": unit.species.code, "species_label": unit.species.label_fr,
                    "code": label.short_code if label else None,
                    "local_name": unit.local_name,
                    "sex": animal.sex if animal else None,
                    "quantity": item.quantity_sent,
                })
            if not animals:
                continue
            flows.append({
                "id": m.id, "occurred_at": m.occurred_at, "received_at": m.received_at,
                "movement_type": m.movement_type, "status": m.status,
                "confidence": movement_confidence(m),
                "from": _flow_place(m.from_center), "to": _flow_place(m.to_center),
                "animals": animals,
                "count": sum(a["quantity"] for a in animals),
            })
        return Response({"days": days, "flows": flows})
