from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.models import Center
from apps.traceability.exceptions import (
    InvalidMovementDataError,
    UnitAlreadyLockedError,
    UnitNotAtOriginCenterError,
)
from apps.traceability.models import Movement
from apps.traceability.serializers import (
    MovementCreateSerializer,
    MovementDetailSerializer,
)
from apps.traceability.services import declare_movement


class MovementListCreateView(APIView):
    """
    Gestion des déclarations de mouvements (MV-01 à MV-03).
    POST /api/movements/ : Déclarer un nouveau mouvement
    GET  /api/movements/ : Lister les mouvements récents
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        center_id = request.query_params.get("center_id")
        qs = Movement.objects.select_related("from_center", "to_center").prefetch_related("items__unit")

        if center_id:
            qs = qs.filter(from_center_id=center_id) | qs.filter(to_center_id=center_id)

        serializer = MovementDetailSerializer(qs[:50], many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MovementCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        movement_id = data.get("operation_id") or data.get("id")
        from_center = Center.objects.get(id=data["from_center_id"])
        to_center = Center.objects.filter(id=data.get("to_center_id")).first() if data.get("to_center_id") else None

        try:
            movement, plain_code = declare_movement(
                movement_id=movement_id,
                from_center=from_center,
                to_center=to_center,
                movement_type=data.get("movement_type", "transfer"),
                items=data["items"],
                created_by=request.user,
                occurred_at=data.get("occurred_at"),
                to_party_note=data.get("to_party_note"),
            )
        except UnitAlreadyLockedError as err:
            return Response(
                {"error": "unit_already_locked", "message": str(err)},
                status=status.HTTP_409_CONFLICT,
            )
        except UnitNotAtOriginCenterError as err:
            return Response(
                {"error": "unit_not_at_origin", "message": str(err)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except InvalidMovementDataError as err:
            return Response(
                {"error": "invalid_movement", "message": str(err)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        detail_serializer = MovementDetailSerializer(movement)
        response_data = detail_serializer.data
        response_data["confirmation_code"] = plain_code

        return Response(response_data, status=status.HTTP_201_CREATED)


class MovementDetailView(APIView):
    """
    GET /api/movements/<id>/ : Détail d'un mouvement
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        movement = Movement.objects.filter(id=pk).first()
        if not movement:
            return Response({"error": "not_found", "message": "Mouvement introuvable."}, status=status.HTTP_404_NOT_FOUND)

        serializer = MovementDetailSerializer(movement)
        return Response(serializer.data)
