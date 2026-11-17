"""Routes /api/auth/. Aucune règle de droits ici : tout passe par services et permissions."""

import math

from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.exceptions import Throttled, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .serializers import (
    AccessSerializer,
    ErrorSerializer,
    LoginSerializer,
    LogoutSerializer,
    MeSerializer,
    RefreshSerializer,
    TokenPairSerializer,
)
from .throttles import LoginIPThrottle, LoginPhoneThrottle

TAG = "Authentification"
LOGIN_FAILED = "Numéro ou mot de passe incorrect."
SESSION_EXPIRED = "Session expirée. Connectez-vous à nouveau."


def _unauthorized(message):
    # Ces vues n'ont pas d'authentification (un vieux jeton ne doit pas bloquer la
    # connexion) : DRF transformerait AuthenticationFailed en 403, on répond 401 nous-mêmes.
    return Response({"detail": message}, status=status.HTTP_401_UNAUTHORIZED,
                    headers={"WWW-Authenticate": 'Bearer realm="api"'})


def _client_ip(request):
    # Même règle que la limitation d'essais (REMOTE_ADDR, ou X-Forwarded-For selon NUM_PROXIES).
    return LoginIPThrottle().get_ident(request)


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [LoginIPThrottle, LoginPhoneThrottle]

    def throttled(self, request, wait):
        minutes = max(1, math.ceil((wait or 60) / 60))
        raise Throttled(wait, detail=f"Trop d'essais. Réessayez dans {minutes} min.")

    @extend_schema(
        tags=[TAG],
        summary="Se connecter (téléphone + mot de passe)",
        description=(
            "Retourne un jeton d'accès et un jeton refresh. Message d'erreur identique "
            "pour un mauvais numéro, un mauvais mot de passe ou un compte désactivé. "
            "Essais limités par numéro et par adresse IP (réponse 429)."
        ),
        auth=[],
        request=LoginSerializer,
        responses={200: TokenPairSerializer, 400: ErrorSerializer, 401: ErrorSerializer,
                   429: ErrorSerializer},
        examples=[OpenApiExample("Vétérinaire de démo",
                                 value={"phone": "+2250000000004", "password": "..."},
                                 request_only=True)],
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.authenticate_by_phone(
            serializer.validated_data["phone"],
            serializer.validated_data["password"],
            ip=_client_ip(request),
        )
        if user is None:
            return _unauthorized(LOGIN_FAILED)
        return Response(services.issue_tokens(user))


class RefreshView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=[TAG],
        summary="Obtenir un nouveau jeton d'accès",
        description="Refusé (401) si le refresh est expiré, en liste noire ou si le compte est désactivé.",
        auth=[],
        request=RefreshSerializer,
        responses={200: AccessSerializer, 401: ErrorSerializer},
    )
    def post(self, request):
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = services.refresh_access(serializer.validated_data["refresh"])
        if data is None:
            return _unauthorized(SESSION_EXPIRED)
        return Response(data)


class LogoutView(APIView):
    @extend_schema(
        tags=[TAG],
        summary="Se déconnecter",
        description=(
            "Met le jeton refresh en liste noire. Rejouable : un refresh déjà en liste "
            "noire renvoie aussi 204. Un refresh d'un autre utilisateur est refusé (400)."
        ),
        request=LogoutSerializer,
        responses={204: None, 400: ErrorSerializer, 401: ErrorSerializer},
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not services.logout(request.user, serializer.validated_data["refresh"]):
            raise ValidationError({"detail": "Jeton invalide."})
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    @extend_schema(
        tags=[TAG],
        summary="Mon profil",
        description=(
            "L'utilisateur connecté uniquement : rôles actifs, habilitation valide "
            "aujourd'hui (oui/non) et centres accessibles (membre ou mandat)."
        ),
        responses={200: MeSerializer, 401: ErrorSerializer},
    )
    def get(self, request):
        from apps.identity.services import accessible_centers  # identity dépend d'accounts

        user = request.user
        data = {
            "id": user.id,
            "phone": user.phone,
            "full_name": user.full_name,
            "language": user.language,
            "is_simulated": user.is_simulated,
            "roles": [
                {
                    "code": m.role.code,
                    "label_fr": m.role.label_fr,
                    "organization": (
                        {"id": m.organization.id, "name": m.organization.name}
                        if m.organization else None
                    ),
                    "zone": (
                        {"id": m.zone.id, "code": m.zone.code, "name": m.zone.name}
                        if m.zone else None
                    ),
                }
                for m in services.active_memberships(user).order_by("role__code")
            ],
            "has_valid_habilitation": services.user_has_valid_habilitation(user),
            "accessible_centers": accessible_centers(user),
        }
        return Response(MeSerializer(data).data)
