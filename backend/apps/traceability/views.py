from django.db.models import Q
from datetime import timedelta
from django.core import signing
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasCenterAccess
from apps.identity.models import Center
from apps.traceability.exceptions import (
    InvalidConfirmationCodeError,
    InvalidMovementDataError,
    MovementNotReceivableError,
    UnitAlreadyLockedError,
    UnitNotAtOriginCenterError,
)
from apps.traceability.models import Movement
from apps.traceability.models import MovementConfirmationCode
from apps.traceability.serializers import (
    MovementConfirmSerializer,
    MovementCreateSerializer,
    MovementDetailSerializer,
    DestinationShareCreateSerializer,
    DestinationShareResolveSerializer,
    DestinationShareResultSerializer,
    ResolvedDestinationSerializer,
)
from apps.traceability.services import (
    confirm_movement_receipt,
    declare_movement,
    generate_confirmation_code,
)
from django.utils import timezone


DESTINATION_SHARE_SALT = "baobia.traceability.destination-share.v1"
DESTINATION_SHARE_MAX_AGE = 30 * 24 * 60 * 60


class DestinationShareCodeView(APIView):
    """Code signé et temporaire pour partager uniquement un élevage destinataire."""

    def get_permissions(self):
        if self.request.method == "POST":
            return [HasCenterAccess.for_scope("move")()]
        return [IsAuthenticated()]

    def get_center_id(self, request):
        return request.data.get("center_id")

    def post(self, request):
        serializer = DestinationShareCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        center = Center.objects.filter(
            pk=serializer.validated_data["center_id"], status="active"
        ).only("id").first()
        if center is None:
            raise NotFound("Élevage introuvable ou fermé.")

        code = signing.dumps(
            {"center_id": str(center.id)},
            salt=DESTINATION_SHARE_SALT,
            compress=True,
        )
        return Response(
            DestinationShareResultSerializer(
                {"code": code, "expires_in_days": 30}
            ).data
        )

    def get(self, request):
        serializer = DestinationShareResolveSerializer(
            data={"code": request.query_params.get("code", "")}
        )
        serializer.is_valid(raise_exception=True)
        try:
            payload = signing.loads(
                serializer.validated_data["code"],
                salt=DESTINATION_SHARE_SALT,
                max_age=DESTINATION_SHARE_MAX_AGE,
            )
        except signing.BadSignature as error:
            raise ValidationError({"code": "Code invalide ou expiré."}) from error

        center = Center.objects.filter(
            pk=payload.get("center_id"), status="active"
        ).only("id", "name").first()
        if center is None:
            raise ValidationError({"code": "Cet élevage n'est plus disponible."})
        return Response(
            ResolvedDestinationSerializer(
                {"center_id": center.id, "center_name": center.name}
            ).data
        )


class MovementListCreateView(APIView):
    """Consulte les mouvements d'un élevage ou en déclare un (MV-01 à MV-03)."""

    permission_classes = [HasCenterAccess.for_scope("move")]

    def get_center_id(self, request):
        if request.method == "POST":
            return request.data.get("from_center_id")
        return request.query_params.get("center_id")

    def get(self, request):
        center_id = self.get_center_id(request)
        movements = (
            Movement.objects.select_related("from_center", "to_center")
            .prefetch_related("items__unit", "status_events", "confirmations")
            .filter(Q(from_center_id=center_id) | Q(to_center_id=center_id))
            .order_by("-occurred_at", "-id")[:50]
        )
        return Response(MovementDetailSerializer(movements, many=True).data)

    def post(self, request):
        serializer = MovementCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        movement_id = data.get("operation_id") or data["id"]

        existing = Movement.objects.filter(pk=movement_id).first()
        if existing:
            if self._same_declaration(existing, data, request.user):
                response_data = MovementDetailSerializer(existing).data
                response_data["confirmation_code"] = self._renew_confirmation_code(existing)
                return Response(response_data, status=status.HTTP_200_OK)
            return Response(
                {"detail": "Cette référence a déjà été utilisée pour une autre déclaration."},
                status=status.HTTP_409_CONFLICT,
            )

        from_center = Center.objects.get(id=data["from_center_id"])
        to_center = (
            Center.objects.filter(id=data.get("to_center_id")).first()
            if data.get("to_center_id")
            else None
        )

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
        except UnitAlreadyLockedError as error:
            return Response(
                {"detail": str(error)}, status=status.HTTP_409_CONFLICT
            )
        except (UnitNotAtOriginCenterError, InvalidMovementDataError) as error:
            raise ValidationError({"detail": str(error)}) from error

        response_data = MovementDetailSerializer(movement).data
        response_data["confirmation_code"] = plain_code
        return Response(response_data, status=status.HTTP_201_CREATED)

    @staticmethod
    def _renew_confirmation_code(movement):
        now = timezone.now()
        movement.confirmation_codes.filter(used_at__isnull=True, expires_at__gt=now).update(
            expires_at=now
        )
        plain_code, code_hash = generate_confirmation_code()
        MovementConfirmationCode.objects.create(
            movement=movement,
            code_hash=code_hash,
            expires_at=now + timedelta(days=7),
        )
        return plain_code

    @staticmethod
    def _same_declaration(movement, data, user):
        requested_items = sorted(
            (str(item.get("unit_id") or item["unit"].id), item.get("quantity_sent", 1))
            for item in data["items"]
        )
        existing_items = sorted(
            (str(item.unit_id), item.quantity_sent)
            for item in movement.items.all()
        )
        return (
            movement.created_by_id == user.id
            and movement.from_center_id == data["from_center_id"]
            and movement.to_center_id == data.get("to_center_id")
            and movement.movement_type == data.get("movement_type", "transfer")
            and movement.to_party_note == data.get("to_party_note")
            and requested_items == existing_items
        )


class MovementDetailView(APIView):
    """Détail visible seulement depuis un élevage auquel la personne a accès."""

    permission_classes = [HasCenterAccess.for_scope("move")]

    def get_center_id(self, request):
        return request.query_params.get("center_id")

    def get(self, request, pk):
        center_id = self.get_center_id(request)
        movement = Movement.objects.filter(pk=pk).filter(
            Q(from_center_id=center_id) | Q(to_center_id=center_id)
        ).first()
        if movement is None:
            raise NotFound("Mouvement introuvable.")
        return Response(MovementDetailSerializer(movement).data)


class MovementConfirmView(APIView):
    """Confirme la réception avec un code, sous l'accès du centre destinataire (MV-04/05/07)."""

    permission_classes = [HasCenterAccess.for_scope("move")]

    def get_center_id(self, request):
        return request.data.get("center_id")

    def post(self, request, pk):
        serializer = MovementConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            movement = confirm_movement_receipt(
                movement_id=pk,
                receiver_center_id=data["center_id"],
                code=data["code"],
                confirmation_id=data["id"],
                created_by=request.user,
            )
        except InvalidConfirmationCodeError as error:
            raise ValidationError({"detail": str(error)}) from error
        except MovementNotReceivableError as error:
            raise NotFound(str(error)) from error
        return Response(MovementDetailSerializer(movement).data, status=status.HTTP_200_OK)
