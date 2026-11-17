"""Fonctions publiques du module audit.

Les autres modules écrivent dans le journal uniquement via `record_event`.
Le journal est en ajout seul (protégé aussi par un trigger SQL).
"""

from .models import AuditLog

# Toute clé contenant un de ces mots est retirée de `details`, à toute profondeur.
_FORBIDDEN_KEY_PARTS = ("password", "token", "secret", "refresh", "access", "otp", "code_hash")


def _is_forbidden(key):
    key = str(key).lower()
    return any(part in key for part in _FORBIDDEN_KEY_PARTS)


def _scrub(value):
    if isinstance(value, dict):
        return {k: _scrub(v) for k, v in value.items() if not _is_forbidden(k)}
    if isinstance(value, (list, tuple)):
        return [_scrub(v) for v in value]
    return value


def record_event(
    action,
    *,
    actor_user=None,
    entity_table="app_user",
    entity_id=None,
    details=None,
    device=None,
):
    """Ajoute une ligne au journal d'audit et la retourne.

    - `action` : verbe pointé, ex. "auth.login", "habilitation.verify".
    - `details` : contexte utile (ip, raison...). Jamais de mot de passe, de jeton
      ni de code : ces clés sont retirées automatiquement par sécurité.
    """
    return AuditLog.objects.create(
        action=action,
        actor_user=actor_user,
        device=device,
        entity_table=entity_table,
        entity_id=entity_id,
        details=_scrub(details or {}),
    )
