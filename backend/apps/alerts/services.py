"""Fonctions publiques du module alerts (responsable : Yéo).

Règles absolues (docs/BAOBIA_DB_SPEC.md) appliquées ici :
- aucune valeur sanitaire dans le code : fenêtres, profondeur, seuils viennent de
  disease_rule (la règle utilisée est gardée dans alert.rule) ;
- « exposé » n'est jamais « contaminé » ;
- niveau 3 seulement par un vétérinaire habilité (contrôlé ici ET par la base) ;
- l'éleveur exposé reçoit un message neutre, sans l'élevage d'origine.

Fonctions :
- current_rule(disease, species, at=None)
- handle_report_review(report, review) : appelée par le signal health.report_reviewed
- compute_exposures(alert, actor) : calcul rejouable (nouveau run_id à chaque fois)
- recompute_zone_stats() : états de la carte (écrits par geo.services)
- visible_alerts(user), is_professional_for_alert(user, alert)
"""

import uuid
from collections import deque
from datetime import timedelta

from django.db import transaction
from django.db.models import F, Q, Sum
from django.utils import timezone

from apps.audit.services import record_event
from apps.health.models import HealthReport
from apps.health.services import HealthError
from apps.identity.models import Center, CenterMember, Lot, TrackedUnit
from apps.traceability.models import Movement

from .models import (
    Alert,
    AlertEvent,
    AlertExposure,
    AlertExposureStep,
    AlertReport,
    DiseaseRule,
)

# Statuts de mouvement pris en compte (contrat docs/CONTRAT_SANTE_MOUVEMENTS.md, B.3).
COUNTED_STATUSES = ("confirmed", "partial", "disputed")
UNCONFIRMED_STATUSES = ("declared",)
OPEN_STATUSES = ("open", "monitoring")
PROFESSIONAL_ROLES = ("veterinarian", "authority")


class AlertsError(HealthError):
    """Erreur métier du module alerts ; message lisible. Hérite de HealthError pour
    qu'une évaluation refusée par alerts soit renvoyée proprement par l'API health."""


# ---------------------------------------------------------------------------
# Règles
# ---------------------------------------------------------------------------


def current_rule(disease, species=None, at=None):
    """Dernière version de règle valide à la date `at` pour la maladie ; une règle
    propre à l'espèce passe avant une règle « toutes espèces »."""
    day = timezone.localdate(at) if at else timezone.localdate()
    rules = DiseaseRule.objects.filter(disease=disease, valid_from__lte=day).filter(
        Q(valid_to__isnull=True) | Q(valid_to__gte=day)
    )
    if species is not None:
        specific = rules.filter(species=species).order_by("-version").first()
        if specific:
            return specific
    return rules.filter(species__isnull=True).order_by("-version").first()


# ---------------------------------------------------------------------------
# Journal de l'alerte
# ---------------------------------------------------------------------------


def _event(alert, event_type, actor, payload=None):
    return AlertEvent.objects.create(
        alert=alert, event_type=event_type, payload=payload or {}, occurred_at=timezone.now(),
        created_by=actor, is_simulated=alert.is_simulated,
    )


# ---------------------------------------------------------------------------
# Réaction à l'évaluation d'un signalement (parcours single_report)
# ---------------------------------------------------------------------------


def _report_species(report):
    unit = (
        TrackedUnit.objects.filter(pk__in=report.subjects.values("unit_id"))
        .select_related("species").first()
    )
    return unit.species if unit else None


def _alert_for_report(report):
    return (
        Alert.objects.select_for_update()
        .filter(trigger_kind="single_report", status__in=OPEN_STATUSES,
                pk__in=AlertReport.objects.filter(report=report).values("alert_id"))
        .first()
    )


def _open_alert_for_focus(report, disease, species):
    """Alerte ouverte du même foyer, pour la même maladie et la même espèce (règle de
    l'alerte) : un 2e signalement validé y est rattaché au lieu d'ouvrir un doublon."""
    species_q = Q(species=species) if species is not None else Q(species__isnull=True)
    return (
        Alert.objects.select_for_update()
        .filter(species_q, trigger_kind="single_report", status__in=OPEN_STATUSES,
                focus_center_id=report.center_id, disease=disease)
        .order_by("opened_at")
        .first()
    )


def _other_active_reports(alert, report):
    """Autres signalements de l'alerte qui ne sont ni refusés ni clôturés."""
    return AlertReport.objects.filter(alert=alert).exclude(report=report).filter(
        report__status__in=("submitted", "under_review", "validated")
    ).exists()


def handle_report_review(report, review):
    """Fait évoluer l'alerte liée au signalement selon la décision du vétérinaire.

    - raise_level2 (maladie choisie) : alerte niveau 2, expositions calculées, visibles
      des seuls professionnels ; aucun message aux éleveurs.
    - validate_level3 : alerte niveau 3 (validée), expositions recalculées, messages
      neutres aux élevages exposés.
    - dismiss : alerte ouverte annulée. close : alerte ouverte clôturée. Si l'alerte a
      d'autres signalements encore actifs, elle reste ouverte (seul ce signalement sort).
    - request_info, retain_suspicion : rien ne change côté alertes.
    Une seule alerte ouverte par foyer, maladie et espèce : un 2e signalement validé au
    même élevage est rattaché à l'alerte ouverte (pas de doublon).
    Appelée dans la transaction de l'évaluation : une erreur annule l'évaluation.
    """
    vet = review.created_by
    alert = _alert_for_report(report)

    if review.decision in ("dismiss", "close"):
        if alert and _other_active_reports(alert, report):
            _event(alert, "reviewed", vet, {"review_id": str(review.pk),
                                            "decision": review.decision,
                                            "report_id": str(report.pk), "alert_kept": True})
            return alert
        if alert:
            alert.status = "cancelled" if review.decision == "dismiss" else "closed"
            alert.closed_at = timezone.now()
            alert.save(update_fields=["status", "closed_at", "updated_at"])
            _event(alert, alert.status, vet, {"review_id": str(review.pk)})
            notify_end(alert, vet)
            recompute_zone_stats()
        return alert

    if review.decision not in ("raise_level2", "validate_level3"):
        return alert

    level = 3 if review.decision == "validate_level3" else 2
    disease = review.disease or (alert.disease if alert else None)
    if disease is None:
        if alert is None:
            return None  # suspicion renforcée sans maladie : pas encore d'alerte
        disease = alert.disease
    species = _report_species(report)

    attached = False
    if alert is None:
        alert = _open_alert_for_focus(report, disease, species)
        if alert is not None:
            AlertReport.objects.create(alert=alert, report=report)
            attached = True

    if alert is None:
        rule = current_rule(disease, species, at=report.occurred_at)
        if rule is None:
            raise AlertsError(
                f"Aucune règle sanitaire pour « {disease.label_fr} ». "
                "Elle doit être ajoutée par l'autorité vétérinaire."
            )
        alert = Alert.objects.create(
            disease=disease, rule=rule, trigger_kind="single_report",
            focus_center=report.center, zone_id=report.center.zone_id, species=species,
            level=level, opened_at=timezone.now(), is_simulated=report.is_simulated,
            **_validation_fields(level, vet, review),
        )
        AlertReport.objects.create(alert=alert, report=report)
        _event(alert, "opened", vet, {"report_id": str(report.pk), "level": level,
                                      "rule_id": str(rule.pk), "rule_version": rule.version})
    elif level > alert.level:
        previous = alert.level
        alert.level = level
        for field, value in _validation_fields(level, vet, review).items():
            setattr(alert, field, value)
        alert.save(update_fields=["level", "validated_by", "validated_at", "habilitation",
                                  "updated_at"])
        _event(alert, "level_changed", vet, {"from": previous, "to": level})

    _event(alert, "reviewed", vet, {"review_id": str(review.pk), "decision": review.decision,
                                    "report_id": str(report.pk), "attached": attached})
    record_event("alert.level", actor_user=vet, entity_table="alert", entity_id=alert.pk,
                 details={"level": alert.level, "report_id": str(report.pk)})
    compute_exposures(alert, vet)
    if alert.level == 3:
        notify_exposed(alert, vet)
    recompute_zone_stats()
    return alert


def _validation_fields(level, vet, review):
    if level < 3:
        return {}
    return {"validated_by": vet, "validated_at": review.occurred_at,
            "habilitation": review.habilitation}


# ---------------------------------------------------------------------------
# Moteur d'exposition (spec 9.6)
# ---------------------------------------------------------------------------


def _start_centers(alert):
    if alert.focus_center_id:
        return [alert.focus_center_id]
    return list(
        HealthReport.objects.filter(
            pk__in=AlertReport.objects.filter(alert=alert).values("report_id")
        ).values_list("center_id", flat=True).distinct()
    )


def _reference_date(alert):
    first = HealthReport.objects.filter(
        pk__in=AlertReport.objects.filter(alert=alert).values("report_id")
    ).order_by("occurred_at").values_list("occurred_at", flat=True).first()
    return first or alert.opened_at


def _arrival(movement):
    return movement.received_at or movement.occurred_at


@transaction.atomic
def compute_exposures(alert, actor):
    """Calcule les élevages exposés et les cas écartés ; retourne le run_id.

    Fenêtre = [date de référence - lookback_days, date de référence + lookforward_days],
    la date de référence étant l'observation du premier signalement de l'alerte.
    Depuis chaque élevage de départ (profondeur 0), un élevage est EXPOSÉ s'il a reçu
    des animaux partis d'un élevage exposé (ou du foyer) dans la fenêtre, après que cet
    élevage soit lui-même devenu exposé, jusqu'à max_depth. Les mouvements `declared`
    ne comptent que si la règle a include_unconfirmed. Seuls comptent les mouvements qui
    portent au moins un animal ou lot de l'espèce de l'alerte (si elle en a une).
    Un mouvement parti d'un élevage de départ hors de la fenêtre est enregistré comme
    cas négatif (outside_window).
    Rejouable : chaque calcul a un nouveau run_id, les précédents sont gardés.
    """
    rule = alert.rule
    reference = _reference_date(alert)
    window_start = reference - timedelta(days=rule.lookback_days)
    window_end = reference + timedelta(days=rule.lookforward_days)
    statuses = COUNTED_STATUSES + (UNCONFIRMED_STATUSES if rule.include_unconfirmed else ())
    now = timezone.now()
    run_id = uuid.uuid4()
    # Espèce de l'alerte : un mouvement de porcs ne propage pas une alerte bovine.
    same_species = Q(items__unit__species_id=alert.species_id) if alert.species_id else Q()
    item_of_species = Q(unit__species_id=alert.species_id) if alert.species_id else Q()

    def first_unit(movement):
        return (movement.items.filter(item_of_species)
                .values_list("unit_id", flat=True).order_by("unit_id").first())

    starts = _start_centers(alert)
    # centre -> (profondeur, exposé depuis, dernier contact, chemin)
    reached = {c: (0, window_start, None, []) for c in starts}
    queue = deque(starts)
    while queue:
        center_id = queue.popleft()
        depth, since, _, path = reached[center_id]
        if depth >= rule.max_depth:
            continue
        movements = (
            Movement.objects.filter(from_center_id=center_id, to_center__isnull=False,
                                    status__in=statuses, occurred_at__gte=since,
                                    occurred_at__lte=window_end)
            .filter(same_species).distinct().order_by("occurred_at")
        )
        for movement in movements:
            target = movement.to_center_id
            if target in reached:
                continue  # déjà atteint plus tôt ou par un chemin plus court
            step = {
                "movement": movement, "from_center_id": center_id, "to_center_id": target,
                "unit_id": first_unit(movement),
                "occurred_at": movement.occurred_at,
                "explanation_code": "sent_from_focus" if depth == 0 else "sent_after_exposure",
            }
            reached[target] = (depth + 1, _arrival(movement), _arrival(movement), path + [step])
            queue.append(target)

    exposures = []
    for center_id, (depth, _, last_contact, path) in reached.items():
        if depth == 0:
            continue
        exposures.append(("exposed", center_id, depth, last_contact, path))

    # Cas négatifs : sorties des élevages de départ en dehors de la fenêtre.
    excluded = {}
    outside = (
        Movement.objects.filter(from_center_id__in=starts, to_center__isnull=False)
        .exclude(to_center_id__in=list(reached))
        .filter(Q(occurred_at__lt=window_start) | Q(occurred_at__gt=window_end))
        .filter(same_species).distinct().order_by("-occurred_at")
    )
    for movement in outside:
        excluded.setdefault(movement.to_center_id, ("outside_window", movement))
    not_counted = (
        Movement.objects.filter(from_center_id__in=starts, to_center__isnull=False,
                                occurred_at__gte=window_start, occurred_at__lte=window_end)
        .exclude(status__in=statuses)
        .exclude(to_center_id__in=list(reached))
        .filter(same_species).distinct()
    )
    for movement in not_counted:
        code = "unconfirmed_not_counted" if movement.status == "declared" else \
            f"movement_{movement.status}"
        excluded.setdefault(movement.to_center_id, (code, movement))
    for center_id, (code, movement) in excluded.items():
        exposures.append(("excluded_negative", center_id, 1, _arrival(movement), [{
            "movement": movement, "from_center_id": movement.from_center_id,
            "to_center_id": center_id,
            "unit_id": first_unit(movement),
            "occurred_at": movement.occurred_at, "explanation_code": code,
        }]))

    for status_, center_id, depth, last_contact, path in exposures:
        exposure = AlertExposure.objects.create(
            alert=alert, run_id=run_id, center_id=center_id, exposure_status=status_,
            depth=depth, last_contact_at=last_contact, computed_at=now,
        )
        AlertExposureStep.objects.bulk_create(
            AlertExposureStep(exposure=exposure, step_no=index, **step)
            for index, step in enumerate(path, start=1)
        )

    # Un mouvement contesté, ou déclaré d'un seul côté (v1.4, 9.6), compte (prudence)
    # mais réduit la confiance de l'alerte (contrat CONTRAT_SANTE_MOUVEMENTS.md, B.3).
    # Ne remet jamais « normal ».
    path_statuses = [
        step["movement"].status for status_, *_, path in exposures if status_ == "exposed"
        for step in path
    ]
    disputed = path_statuses.count("disputed")
    one_side = sum(1 for s in path_statuses if s in UNCONFIRMED_STATUSES)
    update_fields = ["current_run_id", "updated_at"]
    if (disputed or one_side) and alert.confidence != "reduced":
        alert.confidence = "reduced"
        update_fields.append("confidence")
    alert.current_run_id = run_id
    alert.save(update_fields=update_fields)
    _event(alert, "recomputed", actor, {
        "run_id": str(run_id), "rule_version": rule.version,
        "disputed_movements": disputed, "one_side_movements": one_side,
        "window_start": window_start.isoformat(), "window_end": window_end.isoformat(),
        "max_depth": rule.max_depth, "include_unconfirmed": rule.include_unconfirmed,
        "exposed": sum(1 for e in exposures if e[0] == "exposed"),
        "excluded": sum(1 for e in exposures if e[0] == "excluded_negative"),
    })
    return run_id


def current_exposures(alert):
    return AlertExposure.objects.filter(alert=alert, run_id=alert.current_run_id)


# ---------------------------------------------------------------------------
# Notifications neutres (RG-13, RG-16)
# ---------------------------------------------------------------------------


def _center_users(center_ids):
    now = timezone.now()
    member_ids = CenterMember.objects.filter(
        center_id__in=center_ids, starts_at__lte=now
    ).filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now)).values_list("user_id", flat=True)
    from django.contrib.auth import get_user_model

    return list(get_user_model().objects.filter(pk__in=member_ids, is_active=True))


def notify_exposed(alert, actor):
    """Message neutre « Contact possible » aux membres des élevages exposés.
    Aucun paramètre : ni élevage d'origine, ni chaîne, ni lieu."""
    from apps.notifications.services import notify_many

    center_ids = current_exposures(alert).filter(exposure_status="exposed") \
        .values_list("center_id", flat=True)
    users = _center_users(list(center_ids))
    sent = notify_many(users, "exposure.contact_possible", alert_id=alert.pk,
                       dedup_prefix=f"{alert.pk}:exp")
    _event(alert, "notified", actor, {"message_code": "exposure.contact_possible",
                                      "recipients": len(sent)})
    return sent


def notify_end(alert, actor):
    """Message neutre « Fin de surveillance » à ceux qui avaient reçu « Contact possible »
    pour cette alerte (clôturée ou annulée). Personne n'avait été prévenu (niveau 2) :
    aucun message. Aucun paramètre, comme pour le premier message."""
    from apps.accounts.models import User
    from apps.notifications.models import Notification
    from apps.notifications.services import notify_many

    user_ids = Notification.objects.filter(
        alert=alert, message_code="exposure.contact_possible").values_list("user_id", flat=True)
    users = list(User.objects.filter(pk__in=list(user_ids)))
    if not users:
        return []
    sent = notify_many(users, "exposure.ended", alert_id=alert.pk, dedup_prefix=f"{alert.pk}:end")
    _event(alert, "notified", actor, {"message_code": "exposure.ended", "recipients": len(sent)})
    return sent


# ---------------------------------------------------------------------------
# Carte (spec 9.8)
# ---------------------------------------------------------------------------


def _min_zone_effectif():
    today = timezone.localdate()
    value = (
        DiseaseRule.objects.filter(valid_from__lte=today)
        .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=today))
        .order_by("min_zone_effectif").values_list("min_zone_effectif", flat=True).first()
    )
    return value if value is not None else DiseaseRule._meta.get_field("min_zone_effectif").default


def recompute_zone_stats():
    """Recalcule l'état de chaque zone qui a des élevages, toutes espèces confondues
    et par espèce. L'état le plus grave l'emporte (alert > exposure > watch > normal) ;
    une zone sous l'effectif minimum est masquée (« Pas assez de données »).
    RG-14 : un signalement pas encore examiné ne change pas la carte (visible de tous) ;
    seule une décision du vétérinaire (alerte ouverte) peut la faire passer « À surveiller ».
    Une zone compte aussi les élevages de ses zones filles (région -> district -> pays) :
    la carte colore chaque niveau."""
    from apps.geo.models import Zone
    from apps.geo.services import save_zone_stat

    threshold = _min_zone_effectif()
    parents = dict(Zone.objects.values_list("id", "parent_id"))

    def with_ancestors(zone_id):
        while zone_id is not None:
            yield zone_id
            zone_id = parents.get(zone_id)

    centers = Center.objects.filter(status="active").values("id", "zone_id")
    by_zone = {}
    subtree = {}  # zone -> elle-même et ses zones filles (pour les alertes de zone)
    for center in centers:
        for zone_id in with_ancestors(center["zone_id"]):
            by_zone.setdefault(zone_id, set()).add(center["id"])
            subtree.setdefault(zone_id, set()).add(center["zone_id"])

    open_alerts = list(Alert.objects.filter(status__in=OPEN_STATUSES))
    for alert in open_alerts:
        for zone_id in with_ancestors(alert.zone_id):
            subtree.setdefault(zone_id, set()).add(alert.zone_id)
    exposed_pairs = set(
        AlertExposure.objects.filter(
            alert__status__in=OPEN_STATUSES, alert__current_run_id=F("run_id"),
            exposure_status="exposed",
        ).values_list("center_id", "alert__species_id")
    )
    units = TrackedUnit.objects.filter(life_status="active", current_center__isnull=False)
    species_ids = set(units.values_list("species_id", flat=True))
    now = timezone.now()

    for zone_id, center_ids in by_zone.items():
        for species_id in [None, *species_ids]:
            zone_units = units.filter(current_center_id__in=center_ids)
            if species_id:
                zone_units = zone_units.filter(species_id=species_id)
            animals = zone_units.filter(kind="animal").count() + (
                Lot.objects.filter(unit__in=zone_units.filter(kind="lot"))
                .aggregate(total=Sum("current_size"))["total"] or 0
            )
            if species_id and not animals:
                continue

            def matches(alert):
                return species_id is None or alert.species_id in (None, species_id)

            zone_alerts = [a for a in open_alerts if matches(a) and (
                a.zone_id in subtree[zone_id] or a.focus_center_id in center_ids)]
            if any(a.level == 3 for a in zone_alerts):
                state = "alert"
            elif any(c in center_ids and (species_id is None or s in (None, species_id))
                     for c, s in exposed_pairs):
                state = "exposure"
            elif zone_alerts:
                state = "watch"
            else:
                state = "normal"
            save_zone_stat(zone_id=zone_id, species_id=species_id, state=state,
                           centers_count=len(center_ids), animals_count=animals,
                           is_masked=len(center_ids) < threshold, computed_at=now)


# ---------------------------------------------------------------------------
# Lecture et droits
# ---------------------------------------------------------------------------


def _covered_zone_ids(user):
    from apps.health.services import _covered_zone_ids as covered

    return covered(user)


def visible_alerts(user):
    """Alertes visibles par un vétérinaire ou une autorité : celles de ses zones.
    Les éleveurs ne voient pas les alertes : ils reçoivent des messages neutres."""
    return Alert.objects.filter(zone_id__in=_covered_zone_ids(user))


def is_professional_for_alert(user, alert):
    return alert.zone_id in _covered_zone_ids(user)
