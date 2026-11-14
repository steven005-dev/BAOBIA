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
- notify_zone_vets(zone_id, message_code, *, alert_id, round_no=0, params=None,
                   include_ancestors=True)  -> list[Notification]
- mark_read(user, ids=None)  (ids=None : tout marquer lu)
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
    # Éleveur : alerte validée par le vétérinaire dans sa zone.
    "alert.validated": ("alert", ("species",)),
    # Vétérinaires de la zone : regroupement de signalements à confirmer ou infirmer.
    "zone_cluster.review_requested": ("zone_cluster_review", ("species", "reports", "zone")),
    # Relance : personne n'a répondu dans le délai de la règle.
    "zone_cluster.escalated": ("escalation", ("species", "reports", "zone")),
    # Autorité : deux vétérinaires ont pris des décisions différentes (décision D11).
    "alert.review_disagreement": ("alert", ("zone",)),
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
