"""Fonctions publiques du module notifications.

Les autres modules (alerts, health...) n'écrivent JAMAIS dans la table notification :
ils appellent ces fonctions.

Règle de visibilité (spec, règle absolue 9) : un message ne contient jamais l'identité
de l'élevage d'origine. Pour le garantir, chaque `message_code` est déclaré dans
MESSAGES avec la liste fermée des paramètres permis ; tout autre paramètre est refusé.
Le texte affiché est choisi par l'application (vocabulaire officiel), pas par le serveur.

Écriture :
- notify(user, message_code, *, alert_id=None, params=None, dedup_key=None, channel="in_app")
- notify_many(users, message_code, *, dedup_prefix, alert_id=None, params=None)
- mark_alert_messages_read(*, alert_id, message_code)
- notify_zone_vets(zone_id, message_code, *, alert_id, round_no=0, params=None,
                   include_ancestors=True)  -> list[Notification]
- mark_read(user, ids=None)  (ids=None : tout marquer lu)
Événements (21/11, tous les acteurs) :
- on_report_submitted(report)            -> vétérinaires de la zone
- on_report_reviewed(report, review)     -> membres et agents de l'élevage (signal health)
- on_alert_validated(alert) / on_alert_closed(alert) -> autorité de la zone
- on_movement_status(event)              -> l'élevage d'en face (signal post_save)
Lecture :
- unread_count(user), latest_for(user, limit=50)

Exemple (alerts.services, alerte de zone) :
    from apps.notifications.services import notify_zone_vets
    sent = notify_zone_vets(alert.zone_id, "zone_cluster.review_requested",
                            alert_id=alert.id, params={"species": "cattle", "reports": 4})
    if not sent: ...  # aucun vétérinaire habilité : relancer au niveau au-dessus
"""

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.services import vets_for_zone

from .models import Notification


class NotificationError(Exception):
    """Erreur de programmation : message inconnu ou paramètre interdit."""


# message_code -> (kind, paramètres permis). Ajouter un message = l'ajouter ici ET dans
# frontend/src/lib/vocabulaire.ts (texte). Jamais de nom, d'id ou de lieu d'élevage.
MESSAGES = {
    # Éleveur dont l'élevage est exposé (charte : « Contact possible »).
    "exposure.contact_possible": ("exposure", ()),
    # Même éleveur, quand l'alerte est clôturée ou annulée : fin de surveillance.
    "exposure.ended": ("exposure", ()),
    # Éleveur : alerte validée par le vétérinaire dans sa zone.
    "alert.validated": ("alert", ("species",)),
    # Vétérinaires de la zone : regroupement de signalements à confirmer ou infirmer.
    "zone_cluster.review_requested": ("zone_cluster_review", ("species", "reports", "zone")),
    # Relance : personne n'a répondu dans le délai de la règle.
    "zone_cluster.escalated": ("escalation", ("species", "reports", "zone")),
    # Autorité : deux vétérinaires ont pris des décisions différentes (décision D11).
    "alert.review_disagreement": ("alert", ("zone",)),
    # Déclarant d'une disparition ou d'un vol, et Autorité de la zone : l'animal a été scanné
    # dans un marché (traceability, ajout 3). Ni marché, ni animal, ni personne dans le texte.
    "declared_missing.seen": ("declared_missing", ()),
    # --- 21/11 : tous les acteurs reçoivent des messages (voir les fonctions on_* plus bas).
    # Vétérinaires habilités de la zone : nouveau signalement à examiner.
    "report.to_review": ("review", ("species", "count", "report_id")),
    # Membres et agents de l'élevage : le vétérinaire a examiné le signalement.
    "report.reviewed": ("report", ("decision", "report_id")),
    # Autorité de la zone : alerte validée (niveau 3), puis close.
    "alert.authority_validated": ("alert", ("disease", "zone")),
    "alert.authority_closed": ("alert", ("disease", "zone")),
    # Mouvements : l'élevage d'en face est prévenu (jamais le nom d'un élevage).
    "movement.to_confirm": ("movement", ("count",)),
    "movement.declared_by_other": ("movement", ("count",)),
    "movement.confirmed": ("movement", ("count",)),
    "movement.disputed": ("movement", ("count",)),
    "movement.cancelled": ("movement", ("count",)),
}

SIMPLE_TYPES = (str, int, float, bool)


def _check(message_code, params):
    if message_code not in MESSAGES:
        raise NotificationError(f"Message inconnu : {message_code}")
    kind, allowed = MESSAGES[message_code]
    params = dict(params or {})
    extra = set(params) - set(allowed)
    if extra:
        raise NotificationError(f"Paramètre interdit pour {message_code} : {sorted(extra)}")
    if any(not isinstance(v, SIMPLE_TYPES) for v in params.values()):
        raise NotificationError("Les paramètres doivent être des valeurs simples.")
    return kind, params


def notify(user, message_code, *, alert_id=None, params=None, dedup_key=None, channel="in_app"):
    """Crée un message pour `user`. Idempotent avec `dedup_key` : renvoie le message
    existant au lieu d'en créer un second. Dans l'application (in_app), le message est
    disponible tout de suite (statut "sent") ; SMS et push restent "pending" (P2)."""
    kind, params = _check(message_code, params)
    if dedup_key:
        existing = Notification.objects.filter(dedup_key=dedup_key).first()
        if existing:
            return existing
    now = timezone.now()
    in_app = channel == Notification.Channel.IN_APP
    try:
        with transaction.atomic():
            return Notification.objects.create(
                user=user, alert_id=alert_id, kind=kind, message_code=message_code,
                params=params, channel=channel, dedup_key=dedup_key,
                status=Notification.Status.SENT if in_app else Notification.Status.PENDING,
                sent_at=now if in_app else None,
            )
    except IntegrityError:
        # Deux appels simultanés avec la même clé : l'autre a gagné.
        if dedup_key:
            return Notification.objects.get(dedup_key=dedup_key)
        raise


def mark_alert_messages_read(*, alert_id, message_code):
    """Marque lus les messages `message_code` d'une alerte (ex. « Contact possible » quand
    arrive « Fin de surveillance ») : l'éleveur ne voit plus deux messages contraires à
    l'accueil ; ils restent dans son historique. Retourne le nombre de messages marqués."""
    return Notification.objects.filter(
        alert_id=alert_id, message_code=message_code, read_at__isnull=True,
    ).update(status=Notification.Status.READ, read_at=timezone.now())


def notify_many(users, message_code, *, dedup_prefix, alert_id=None, params=None):
    """Un message par utilisateur ; clé anti-doublon = `<dedup_prefix>:<user_id>`.
    `dedup_prefix` doit tenir en 43 caractères (la clé fait 80 au plus)."""
    if len(dedup_prefix) > 80 - 37:
        raise NotificationError("dedup_prefix trop long.")
    return [
        notify(user, message_code, alert_id=alert_id, params=params,
               dedup_key=f"{dedup_prefix}:{user.pk}")
        for user in users
    ]


def notify_zone_vets(zone_id, message_code, *, alert_id, round_no=0, params=None,
                     include_ancestors=True):
    """Prévient les vétérinaires habilités de la zone (et des zones parentes).

    `round_no` : 0 au premier envoi, 1, 2... à chaque relance ; un même vétérinaire ne
    reçoit qu'un message par alerte et par tour. Liste vide = personne à prévenir :
    à l'appelant de relancer au niveau au-dessus (zone parente) ou vers l'autorité.
    """
    if alert_id is None:
        raise NotificationError("alert_id est obligatoire pour prévenir les vétérinaires.")
    vets = vets_for_zone(zone_id, include_ancestors=include_ancestors)
    # uuid (36) + ":" + tour : tient dans 43 caractères tant que round_no < 10**5.
    return notify_many(vets, message_code, alert_id=alert_id, params=params,
                       dedup_prefix=f"{alert_id}:{round_no}")


def mark_read(user, ids=None):
    """Marque comme lus les messages de `user` (tous si `ids` est None). Retourne le nombre.
    Les messages d'un autre utilisateur ne sont jamais touchés."""
    qs = Notification.objects.filter(user=user, read_at__isnull=True)
    if ids is not None:
        qs = qs.filter(pk__in=list(ids))
    return qs.update(status=Notification.Status.READ, read_at=timezone.now())


def unread_count(user):
    return Notification.objects.filter(user=user, read_at__isnull=True).count()


def latest_for(user, limit=50):
    return Notification.objects.filter(user=user).order_by("-created_at")[:limit]


# ---------------------------------------------------------------------------
# Événements : qui est prévenu de quoi (21/11). Messages dans l'application ;
# jamais le nom d'un élevage, ni pour les éleveurs ni dans les mouvements.
# ---------------------------------------------------------------------------


def _without(users, actor_id):
    return [u for u in users if u.pk != actor_id]


def on_report_submitted(report):
    """Nouveau signalement : les vétérinaires habilités de la zone (et zones parentes)."""
    unit = report.subjects.select_related("unit__species").first()
    params = {"count": report.affected_count, "report_id": str(report.pk)}
    if unit:
        params["species"] = unit.unit.species.label_fr
    vets = _without(vets_for_zone(report.center.zone_id), report.created_by_id)
    return notify_many(vets, "report.to_review", params=params, dedup_prefix=f"rep:{report.pk}")


def on_report_reviewed(report, review):
    """Décision du vétérinaire : les membres et agents de l'élevage (pas le vétérinaire)."""
    from apps.identity.services import center_contacts

    users = _without(center_contacts([report.center_id]), review.created_by_id)
    return notify_many(users, "report.reviewed",
                       params={"decision": review.decision, "report_id": str(report.pk)},
                       dedup_prefix=f"rev:{review.pk}")


def _alert_params(alert):
    return {"disease": alert.disease.label_fr if alert.disease_id else "",
            "zone": alert.zone.name}


def on_alert_validated(alert):
    """Alerte validée (niveau 3) : l'autorité dont le périmètre couvre la zone."""
    from apps.accounts.services import authorities_for_zone

    return notify_many(authorities_for_zone(alert.zone_id), "alert.authority_validated",
                       alert_id=alert.pk, params=_alert_params(alert),
                       dedup_prefix=f"{alert.pk}:av")


def on_alert_closed(alert):
    """Alerte clôturée ou annulée : la même autorité."""
    from apps.accounts.services import authorities_for_zone

    return notify_many(authorities_for_zone(alert.zone_id), "alert.authority_closed",
                       alert_id=alert.pk, params=_alert_params(alert),
                       dedup_prefix=f"{alert.pk}:ac")


def on_movement_status(event):
    """Chaque étape d'un mouvement prévient l'élevage d'en face, jamais celui qui agit :
    - déclaré : la destination doit confirmer ; si ce n'est pas l'origine qui déclare
      (entrée au marché), l'origine est aussi prévenue (utile contre le vol) ;
    - confirmé ou partiel : l'origine ; contesté : les deux côtés ; annulé : la destination."""
    from apps.identity.services import center_contacts

    movement = event.movement
    origin, target = movement.from_center_id, movement.to_center_id
    actor = event.created_by_id
    params = {"count": movement.items.count()}
    sends = []
    if event.status == "declared":
        if target:
            sends.append(("movement.to_confirm", [target]))
        origin_ids = {u.pk for u in center_contacts([origin])}
        if actor not in origin_ids:
            sends.append(("movement.declared_by_other", [origin]))
    elif event.status in ("confirmed", "partial"):
        sends.append(("movement.confirmed", [origin]))
    elif event.status == "disputed":
        sends.append(("movement.disputed", [c for c in (origin, target) if c]))
    elif event.status == "cancelled" and target:
        sends.append(("movement.cancelled", [target]))
    sent = []
    for index, (code, centers) in enumerate(sends):
        users = _without(center_contacts(centers), actor)
        sent += notify_many(users, code, params=params, dedup_prefix=f"mv:{event.pk}:{index}")
    return sent
