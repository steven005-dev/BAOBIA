"""Fonctions publiques du module health (responsable : Yéo).

Les autres modules n'écrivent JAMAIS dans les tables de health : ils appellent
ces fonctions. La colonne CALCULÉ health_report.status n'est écrite qu'ici.

Catalogue :
- load_catalog() : maladies et symptômes de départ (idempotent)
Signalement (contrat avec la file hors ligne, docs/CONTRAT_SANTE_MOUVEMENTS.md) :
- submit_report(...) : crée un signalement ; rejouer la même opération est sans effet
Évaluation vétérinaire :
- review_report(...) : enregistre la décision, met à jour le statut, émet report_reviewed
Droits de lecture :
- can_submit_for_center, visible_reports, can_review_report
"""

from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.services import get_valid_habilitation, user_has_role
from apps.audit.services import record_event
from apps.core.models import Species
from apps.identity.models import Center, TrackedUnit
from apps.identity.services import (
    accessible_centers,
    user_can_access_center,
    user_covers_zone,
)

from . import catalog
from .models import (
    Disease,
    DiseaseSpecies,
    HealthReport,
    HealthReportReview,
    HealthReportSubject,
    HealthReportSymptom,
    Symptom,
    SymptomSpecies,
)
from .signals import report_reviewed

# Rôles professionnels qui voient les signalements de leur zone (et des zones filles).
PROFESSIONAL_ROLES = ("veterinarian", "authority")

# Statut (cache) du signalement après chaque décision du vétérinaire.
STATUS_AFTER_DECISION = {
    "request_info": "under_review",
    "retain_suspicion": "under_review",
    "raise_level2": "under_review",
    "validate_level3": "validated",
    "dismiss": "rejected",
    "close": "closed",
}


class HealthError(Exception):
    """Erreur métier du module health ; le message est lisible par l'utilisateur."""


class HealthForbidden(HealthError):
    """Refus de droits (403) : pas d'accès à l'élevage, habilitation ou zone."""


class ReportConflict(HealthError):
    """Le même identifiant existe déjà avec un autre contenu (opération « À vérifier »)."""


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------


@transaction.atomic
def load_catalog():
    """Crée les maladies et symptômes du catalogue de départ, et leurs espèces.

    Idempotent : ne crée que ce qui manque, ne modifie jamais une ligne existante.
    Exige les espèces du seed de core. Retourne la liste des éléments créés.
    """
    codes = {code for *_, species in (*catalog.DISEASES, *catalog.SYMPTOMS) for code in species}
    species = {s.code: s for s in Species.objects.filter(code__in=codes)}
    missing = sorted(codes - species.keys())
    if missing:
        raise HealthError(
            "Espèces absentes : " + ", ".join(missing) + ". Lancez d'abord manage.py seed."
        )

    created = []
    for code, label, species_codes in catalog.DISEASES:
        disease, is_new = Disease.objects.get_or_create(code=code, defaults={"label_fr": label})
        if is_new:
            created.append(f"maladie {code}")
        for species_code in species_codes:
            DiseaseSpecies.objects.get_or_create(disease=disease, species=species[species_code])

    for code, label, icon, species_codes in catalog.SYMPTOMS:
        symptom, is_new = Symptom.objects.get_or_create(
            code=code, defaults={"label_fr": label, "icon": icon}
        )
        if is_new:
            created.append(f"symptôme {code}")
        for species_code in species_codes:
            SymptomSpecies.objects.get_or_create(symptom=symptom, species=species[species_code])
    return created


# ---------------------------------------------------------------------------
# Droits
# ---------------------------------------------------------------------------


def can_submit_for_center(user, center):
    """Signaler pour un élevage : membre ou mandataire (droit « declare »), ou
    vétérinaire / autorité dont le périmètre couvre la zone de l'élevage."""
    return user_can_access_center(user, center.pk, scope="declare") or user_covers_zone(
        user, center.zone_id, roles=PROFESSIONAL_ROLES
    )


def _covered_zone_ids(user):
    """Zones couvertes par un rôle professionnel actif, avec toutes leurs zones filles."""
    from apps.accounts.services import active_memberships
    from apps.geo.models import Zone

    frontier = set(
        active_memberships(user)
        .filter(role__code__in=PROFESSIONAL_ROLES, zone__isnull=False)
        .values_list("zone_id", flat=True)
    )
    covered = set()
    while frontier:
        covered |= frontier
        frontier = set(
            Zone.objects.filter(parent_id__in=frontier).values_list("id", flat=True)
        ) - covered
    return covered


def visible_reports(user):
    """Signalements qu'un utilisateur peut voir :
    - ceux qu'il a faits ;
    - ceux des élevages auxquels il a accès (membre ou mandat) ;
    - pour un vétérinaire ou une autorité : ceux des zones qu'il couvre.
    """
    center_ids = [center["id"] for center in accessible_centers(user)]
    return HealthReport.objects.filter(
        Q(created_by=user)
        | Q(center_id__in=center_ids)
        | Q(center__zone_id__in=_covered_zone_ids(user))
    ).distinct()


def is_professional_for(user, report):
    """Vrai si l'utilisateur voit le signalement en tant que vétérinaire ou autorité."""
    zone_id = Center.objects.filter(pk=report.center_id).values_list("zone_id", flat=True).first()
    return user_covers_zone(user, zone_id, roles=PROFESSIONAL_ROLES)


def can_review_report(user, report):
    """Vétérinaire, habilitation valide aujourd'hui, zone de l'élevage couverte."""
    return (
        user_has_role(user, "veterinarian")
        and get_valid_habilitation(user) is not None
        and user_covers_zone(user, report.center.zone_id, roles=("veterinarian",))
    )


# ---------------------------------------------------------------------------
# Signalement
# ---------------------------------------------------------------------------


def _decimal_or_none(value):
    return None if value is None else Decimal(str(value))


def _same_report(report, *, user, center, report_kind, affected_count, self_severity,
                 occurred_at, note, latitude, longitude, position_accuracy_m,
                 position_source, symptom_codes, subjects):
    """Vrai si le signalement existant a EXACTEMENT le même contenu que l'envoi rejoué
    (auteur, élevage, champs, position, symptômes, animaux et leur état)."""
    existing_symptoms = set(report.symptoms.values_list("code", flat=True))
    existing_subjects = {
        (str(unit_id), condition, notes or None)
        for unit_id, condition, notes in report.subjects.values_list(
            "unit_id", "condition", "notes")
    }
    requested_subjects = {
        (str(s["unit_id"]), s["condition"], s.get("notes") or None) for s in subjects
    }
    return (
        report.created_by_id == user.pk
        and report.center_id == center.pk
        and report.report_kind == report_kind
        and report.affected_count == affected_count
        and report.self_severity == self_severity
        and report.occurred_at == occurred_at
        and (report.note or None) == (note or None)
        and _decimal_or_none(report.latitude) == _decimal_or_none(latitude)
        and _decimal_or_none(report.longitude) == _decimal_or_none(longitude)
        and _decimal_or_none(report.position_accuracy_m) == _decimal_or_none(position_accuracy_m)
        and report.position_source == position_source
        and existing_symptoms == set(symptom_codes)
        and existing_subjects == requested_subjects
    )


@transaction.atomic
def submit_report(
    *, report_id, user, center, report_kind, affected_count, self_severity, occurred_at,
    symptom_codes=(), subjects=(), note=None, latitude=None, longitude=None,
    position_accuracy_m=None, position_source="none", device=None, is_simulated=False,
):
    """Crée un signalement et retourne (report, created).

    `report_id` = UUID de l'opération créée sur le téléphone (idempotence) :
    - même id, même contenu -> (signalement existant, False), aucun effet ;
    - même id, autre contenu -> ReportConflict.
    `subjects` : liste de {"unit_id", "condition"} ; chaque unité doit être dans l'élevage.
    Le signalement n'a aucun effet visible hors des professionnels avant examen (RG-14).
    Données de démonstration : le signalement est simulé si le compte ou l'élevage l'est
    (il ne doit jamais compter comme un vrai cas, ni l'alerte qui en découle).
    """
    symptom_codes = list(dict.fromkeys(symptom_codes))
    subjects = list(subjects)
    comparable = dict(user=user, center=center, report_kind=report_kind,
                      affected_count=affected_count, self_severity=self_severity,
                      occurred_at=occurred_at, note=note, latitude=latitude,
                      longitude=longitude, position_accuracy_m=position_accuracy_m,
                      position_source=position_source, symptom_codes=symptom_codes,
                      subjects=subjects)

    existing = HealthReport.objects.filter(pk=report_id).first()
    if existing is not None:
        if _same_report(existing, **comparable):
            return existing, False
        raise ReportConflict("Ce signalement existe déjà avec d'autres informations.")

    if not can_submit_for_center(user, center):
        raise HealthForbidden("Vous n'avez pas accès à cet élevage.")
    if center.status != "active":
        raise HealthError("Cet élevage est fermé.")

    symptoms = list(Symptom.objects.filter(code__in=symptom_codes, is_active=True))
    unknown = sorted(set(symptom_codes) - {s.code for s in symptoms})
    if unknown:
        raise HealthError("Symptôme inconnu : " + ", ".join(unknown) + ".")

    unit_ids = [str(s["unit_id"]) for s in subjects]
    if len(set(unit_ids)) != len(unit_ids):
        raise HealthError("Un animal est choisi deux fois.")
    units = {str(u.pk): u for u in TrackedUnit.objects.filter(pk__in=unit_ids)}
    for unit_id in unit_ids:
        unit = units.get(unit_id)
        if unit is None or unit.current_center_id != center.pk:
            raise HealthError("Cet animal n'est pas dans cet élevage.")

    report = HealthReport.objects.create(
        id=report_id,
        center=center,
        report_kind=report_kind,
        affected_count=affected_count,
        self_severity=self_severity,
        note=note or None,
        occurred_at=occurred_at,
        created_by=user,
        device=device,
        latitude=latitude,
        longitude=longitude,
        position_accuracy_m=position_accuracy_m,
        position_source=position_source,
        is_simulated=is_simulated or user.is_simulated or center.is_simulated,
    )
    HealthReportSymptom.objects.bulk_create(
        HealthReportSymptom(report=report, symptom=symptom) for symptom in symptoms
    )
    HealthReportSubject.objects.bulk_create(
        HealthReportSubject(report=report, unit=units[str(s["unit_id"])],
                            condition=s["condition"], notes=s.get("notes") or None)
        for s in subjects
    )
    record_event(
        "health_report.submit", actor_user=user, entity_table="health_report",
        entity_id=report.pk, device=device,
        details={"center_id": str(center.pk), "report_kind": report_kind,
                 "affected_count": affected_count},
    )
    return report, True


# ---------------------------------------------------------------------------
# Évaluation vétérinaire
# ---------------------------------------------------------------------------


@transaction.atomic
def review_report(*, report, vet, decision, disease=None, note=None, occurred_at=None,
                  review_id=None):
    """Enregistre la décision d'un vétérinaire habilité sur un signalement.

    - Refuse si l'utilisateur n'est pas vétérinaire, sans habilitation valide à cet
      instant, ou hors de sa zone (RG-08).
    - Met à jour le cache health_report.status, journalise, puis émet
      `report_reviewed` dans la même transaction (le module alerts y répond).
    - Un signalement clôturé ne s'évalue plus ; un signalement refusé peut être
      ré-évalué. `dismiss` exige un motif.
    """
    report = HealthReport.objects.select_for_update().select_related("center").get(pk=report.pk)
    if decision not in STATUS_AFTER_DECISION:
        raise HealthError("Décision inconnue.")
    habilitation = get_valid_habilitation(vet, at=occurred_at)
    if not user_has_role(vet, "veterinarian") or habilitation is None:
        raise HealthForbidden("Votre habilitation n'est pas valide.")
    if not user_covers_zone(vet, report.center.zone_id, roles=("veterinarian",)):
        raise HealthForbidden("Cet élevage n'est pas dans votre zone.")
    if report.status == "closed":
        raise HealthError("Ce signalement est clôturé.")
    if decision == "dismiss" and not (note or "").strip():
        raise HealthError("Indiquez le motif du refus.")
    if decision == "validate_level3" and disease is None:
        raise HealthError("Choisissez la maladie retenue pour valider.")

    kwargs = {"id": review_id} if review_id else {}
    review = HealthReportReview.objects.create(
        report=report,
        decision=decision,
        disease=disease,
        habilitation=habilitation,
        note=note or None,
        occurred_at=occurred_at or timezone.now(),
        created_by=vet,
        is_simulated=report.is_simulated,
        **kwargs,
    )
    report.status = STATUS_AFTER_DECISION[decision]
    report.save(update_fields=["status"])
    record_event(
        "health_report.review", actor_user=vet, entity_table="health_report",
        entity_id=report.pk,
        details={"decision": decision, "disease": disease.code if disease else None,
                 "habilitation_id": str(habilitation.pk)},
    )
    report_reviewed.send(sender=HealthReport, report=report, review=review)
    return review
