from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.services import record_event

from .serializers import LoginSerializer, LogoutSerializer, RefreshSerializer, UserMeSerializer
from .throttles import LoginAttemptThrottle


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginAttemptThrottle]

    @extend_schema(request=LoginSerializer, responses=LoginSerializer)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class RefreshView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=RefreshSerializer, responses=RefreshSerializer)
    def post(self, request):
        serializer = RefreshSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError:
            return Response({"detail": "Jeton invalide."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.validated_data)


class LogoutView(APIView):
    @extend_schema(request=LogoutSerializer, responses={204: None})
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            RefreshToken(serializer.validated_data["refresh"]).blacklist()
        except TokenError:
            return Response({"detail": "Jeton invalide."}, status=status.HTTP_400_BAD_REQUEST)
        record_event("logout", actor_user=request.user, entity_id=request.user.id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    @extend_schema(responses=UserMeSerializer)
    def get(self, request):
        record_event(
            "habilitation_checked",
            actor_user=request.user,
            entity_id=request.user.id,
            details={"valid": UserMeSerializer(request.user).data["has_valid_habilitation"]},
        )
        return Response(UserMeSerializer(request.user).data)
