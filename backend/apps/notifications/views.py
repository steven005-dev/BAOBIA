"""Routes /api/notifications/ : uniquement les messages de l'utilisateur connecté."""

from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers import ErrorSerializer

from . import services
from .serializers import MarkedSerializer, MarkReadSerializer, NotificationSerializer, UnreadCountSerializer

TAG = "Messages"


class NotificationListView(APIView):
    @extend_schema(
        tags=[TAG],
        summary="Mes messages",
        description="Les 50 derniers messages de l'utilisateur connecté, du plus récent au plus ancien.",
        responses={200: NotificationSerializer(many=True), 401: ErrorSerializer},
    )
    def get(self, request):
        return Response(NotificationSerializer(services.latest_for(request.user), many=True).data)


class UnreadCountView(APIView):
    @extend_schema(
        tags=[TAG],
        summary="Nombre de messages non lus",
        responses={200: UnreadCountSerializer, 401: ErrorSerializer},
    )
    def get(self, request):
        return Response({"unread": services.unread_count(request.user)})


class MarkReadView(APIView):
    @extend_schema(
        tags=[TAG],
        summary="Marquer des messages comme lus",
        description="Seulement mes messages ; rejouer est sans effet.",
        request=MarkReadSerializer,
        responses={200: MarkedSerializer, 400: ErrorSerializer, 401: ErrorSerializer},
    )
    def post(self, request):
        serializer = MarkReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        marked = services.mark_read(request.user, serializer.validated_data.get("ids"))
        return Response({"marked": marked})
