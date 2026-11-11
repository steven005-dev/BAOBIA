"""Permissions DRF réutilisables par tous les modules.

Ne réécrivez pas ces contrôles dans vos vues : importez-les.

    from apps.accounts.permissions import (
        IsAuthenticated, HasRole, HasValidHabilitation, HasCenterAccess,
    )

    class ReviewView(APIView):
        # Vétérinaire ET habilitation valide aujourd'hui (validation niveau 3).
        permission_classes = [HasRole("veterinarian"), HasValidHabilitation]

    class CenterMovementsView(APIView):   # URL : centers/<uuid:center_id>/movements/
        permission_classes = [HasCenterAccess.for_scope("move")]

Par défaut (settings.REST_FRAMEWORK) toute route exige un utilisateur connecté
(IsAuthenticated) : inutile de le répéter, sauf si vous remplacez permission_classes.
Toutes ces permissions renvoient 403 avec un message court en français.
"""

from rest_framework.permissions import BasePermission, IsAuthenticated

from .services import user_has_role, user_has_valid_habilitation

__all__ = ["IsAuthenticated", "HasRole", "HasValidHabilitation", "HasCenterAccess"]


def _is_logged_in(request):
    user = getattr(request, "user", None)
    return bool(user and user.is_authenticated and user.is_active)


def HasRole(*role_codes):
    """Fabrique une permission : l'utilisateur a AU MOINS UN des rôles actifs donnés.

    Exemples : HasRole("veterinarian"), HasRole("authority", "veterinarian").
    Codes : breeder, field_agent, veterinarian, authority, trader.
    """
    if not role_codes:
        raise ValueError("HasRole demande au moins un code de rôle.")

    class _HasRole(BasePermission):
        message = "Vous n'avez pas le rôle demandé."

        def has_permission(self, request, view):
            return _is_logged_in(request) and any(
                user_has_role(request.user, code) for code in role_codes
            )

    _HasRole.__name__ = "HasRole_" + "_".join(role_codes)
    _HasRole.__qualname__ = _HasRole.__name__
    return _HasRole


class HasValidHabilitation(BasePermission):
    """L'utilisateur a une habilitation vétérinaire valide AUJOURD'HUI.

    Valide = statut "verified" et date du jour entre valid_from et valid_to.
    Refusé si "pending", "revoked", "expired" ou hors dates.
    À combiner avec HasRole("veterinarian") pour toute décision sanitaire.
    Pour enregistrer `habilitation_id`, utilisez accounts.services.get_valid_habilitation.
    """

    message = "Votre habilitation n'est pas valide."

    def has_permission(self, request, view):
        return _is_logged_in(request) and user_has_valid_habilitation(request.user)


class HasCenterAccess(BasePermission):
    """L'utilisateur est membre actif du centre (center_member) ou a un mandat actif dessus.

    Où trouver le centre (dans cet ordre) :
    1. `view.get_center_id(request)` si la vue définit cette méthode ;
    2. le paramètre d'URL `center_id` (nom changeable via `view.center_url_kwarg`) ;
    3. `center_id` dans le corps (POST) ou la chaîne de requête (GET).
    Sans centre trouvé : refusé.

    Pour un objet (has_object_permission) : `obj` est un Center, ou a `center_id`,
    ou `current_center_id` (unité suivie). Pour une vue détail où le centre vient
    seulement de l'objet, mettez `center_from_object = True` sur la vue : le contrôle
    se fait alors dans has_object_permission (get_object() doit être appelé).

    `HasCenterAccess.for_scope("move")` ou `("declare")` : un mandat ne compte que s'il
    donne ce droit (ou "all"). Les membres du centre ont toujours accès.
    """

    message = "Vous n'avez pas accès à cet élevage."
    mandate_scope = None

    @classmethod
    def for_scope(cls, scope):
        if scope not in ("declare", "move", "all"):
            raise ValueError("scope doit être 'declare', 'move' ou 'all'.")
        return type(f"HasCenterAccess_{scope}", (cls,), {"mandate_scope": scope})

    def _center_id(self, request, view):
        getter = getattr(view, "get_center_id", None)
        if callable(getter):
            return getter(request)
        kwarg = getattr(view, "center_url_kwarg", "center_id")
        center_id = (getattr(view, "kwargs", None) or {}).get(kwarg)
        if center_id:
            return center_id
        data = request.data if hasattr(request.data, "get") else {}
        return data.get("center_id") or request.query_params.get("center_id")

    def _check(self, request, center_id):
        # Import tardif : identity dépend d'accounts, pas l'inverse.
        from apps.identity.services import user_can_access_center

        return user_can_access_center(request.user, center_id, scope=self.mandate_scope)

    def has_permission(self, request, view):
        if not _is_logged_in(request):
            return False
        if getattr(view, "center_from_object", False):
            return True
        return self._check(request, self._center_id(request, view))

    def has_object_permission(self, request, view, obj):
        if obj.__class__.__name__ == "Center":
            center_id = obj.pk
        else:
            center_id = getattr(obj, "center_id", None) or getattr(obj, "current_center_id", None)
        return _is_logged_in(request) and self._check(request, center_id)
