from django.db.models import Q
from datetime import date, timedelta
from django.core import signing
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasCenterAccess
from apps.identity.models import Center, TrackedUnit
from apps.identity.services import user_can_access_center, user_can_view_unit, user_covers_zone
from apps.traceability.exceptions import (
    InvalidConfirmationCodeError,
    InvalidMovementDataError,
    MovementNotReceivableError,
    OperationConflictError,
    UnitAlreadyLockedError,
    UnitNotAtOriginCenterError,
)
from apps.traceability.models import Movement, MovementConfirmationCode, StatusEvent
from apps.traceability.serializers import (
    MovementConfirmSerializer,
    MovementCreateSerializer,
    MovementDetailSerializer,
    MarketEntrySerializer,
    MarketScanSerializer,
    RfidTagCreateSerializer,
    MarketExitSerializer,
    MovementReasonSerializer,
    MovementRefuseSerializer,
    DestinationShareCreateSerializer,
    DestinationShareResolveSerializer,
    DestinationShareResultSerializer,
    ResolvedDestinationSerializer,
    UnitEventCreateSerializer,
    UnitEventReadSerializer,
)
from apps.traceability.services import (
    active_rfid,
    bind_rfid_tag,
    cancel_movement,
    format_rfid,
    market_summary,
    record_market_scan,
    unit_route,
    confirm_movement_receipt,
    contest_movement,
    declare_market_entry,
    declare_market_exit,
    declare_movement,
    generate_confirmation_code,
    record_unit_event,
    refuse_movement_receipt,
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
            .prefetch_related("items__unit", "status_events", "confirmations__created_by",
                              "discrepancies__unit")
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
                is_simulated=request.user.is_simulated,
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
                occurred_at=data.get("occurred_at"),
                items_received=data.get("items_received"),
            )
        except OperationConflictError as error:
            return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
        except (InvalidConfirmationCodeError, InvalidMovementDataError) as error:
            raise ValidationError({"detail": str(error)}) from error
        except MovementNotReceivableError as error:
            raise NotFound(str(error)) from error
        return Response(MovementDetailSerializer(movement).data, status=status.HTTP_200_OK)


class _MovementActionView(APIView):
    """Action sur un mouvement, sous l'accès de l'élevage indiqué dans `center_id`."""

    permission_classes = [HasCenterAccess.for_scope("move")]
    serializer_class = MovementReasonSerializer

    def get_center_id(self, request):
        return request.data.get("center_id")

    def act(self, request, pk, data):
        raise NotImplementedError

    def post(self, request, pk):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            movement = self.act(request, pk, serializer.validated_data)
        except InvalidMovementDataError as error:
            raise ValidationError({"detail": str(error)}) from error
        except MovementNotReceivableError as error:
            raise NotFound(str(error)) from error
        return Response(MovementDetailSerializer(movement).data, status=status.HTTP_200_OK)


class MovementRefuseView(_MovementActionView):
    """Le destinataire refuse la réception : mouvement contesté (MV-05, MV-09)."""

    serializer_class = MovementRefuseSerializer

    def act(self, request, pk, data):
        return refuse_movement_receipt(
            movement_id=pk, receiver_center_id=data["center_id"], created_by=request.user,
            reason=data["reason"], confirmation_id=data.get("id"),
            occurred_at=data.get("occurred_at"),
        )


class MovementCancelView(_MovementActionView):
    """L'élevage de départ annule un départ pas encore reçu (MV-05)."""

    def act(self, request, pk, data):
        return cancel_movement(
            movement_id=pk, center_id=data["center_id"], created_by=request.user,
            reason=data["reason"], occurred_at=data.get("occurred_at"),
        )


class MovementContestView(_MovementActionView):
    """Une des deux parties conteste un mouvement reçu ; BAOBIA ne tranche pas (MV-09)."""

    def act(self, request, pk, data):
        return contest_movement(
            movement_id=pk, center_id=data["center_id"], created_by=request.user,
            reason=data["reason"], occurred_at=data.get("occurred_at"),
        )


class _MarketView(APIView):
    """Passage au marché (R2, spec 9.11) : membre du marché ou mandat `move` dessus."""

    permission_classes = [HasCenterAccess.for_scope("move")]

    def get_center_id(self, request):
        return request.data.get("market_id")

    def market(self, data):
        market = Center.objects.filter(pk=data["market_id"]).first()
        if market is None:
            raise NotFound("Marché introuvable.")
        return market


class MarketEntryView(_MarketView):
    """Entrée au marché déclarée par le marché seul, sans code (Q1)."""

    def post(self, request):
        serializer = MarketEntrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            movements, created = declare_market_entry(
                market=self.market(data), label_codes=data["label_codes"],
                created_by=request.user, entry_id=data["id"],
                occurred_at=data.get("occurred_at"),
            )
        except (OperationConflictError, UnitAlreadyLockedError) as error:
            return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
        except InvalidMovementDataError as error:
            raise ValidationError({"detail": str(error)}) from error
        return Response(
            {"movements": MovementDetailSerializer(movements, many=True).data},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class MarketExitView(_MarketView):
    """Sortie du marché : vers un élevage inscrit (avec code) ou hors système (Q3)."""

    def post(self, request):
        serializer = MarketExitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        to_center = (Center.objects.filter(pk=data["to_center_id"]).first()
                     if data.get("to_center_id") else None)
        try:
            movement, code, created = declare_market_exit(
                market=self.market(data), label_codes=data["label_codes"],
                created_by=request.user, exit_id=data["id"], to_center=to_center,
                to_party_note=data.get("to_party_note"), occurred_at=data.get("occurred_at"),
            )
        except (OperationConflictError, UnitAlreadyLockedError) as error:
            return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
        except (InvalidMovementDataError, UnitNotAtOriginCenterError) as error:
            raise ValidationError({"detail": str(error)}) from error
        body = MovementDetailSerializer(movement).data
        body["confirmation_code"] = code
        body["out_of_system"] = to_center is None
        return Response(body, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class UnitEventListCreateView(APIView):
    """Événements de vie des unités d'un élevage : décès, abattage, vol... (MV-02).

    MV-13 : vol et disparition ne sont montrés qu'à la personne qui les a déclarés ;
    les professionnels habilités les consultent par leur propre espace.
    """

    def get_permissions(self):
        scope = "declare" if self.request.method == "POST" else "move"
        return [HasCenterAccess.for_scope(scope)()]

    def get_center_id(self, request):
        if request.method == "POST":
            return request.data.get("center_id")
        return request.query_params.get("center_id")

    def get(self, request):
        events = StatusEvent.objects.filter(
            unit__current_center_id=self.get_center_id(request)
        ).filter(Q(visibility__in=("owner", "all")) | Q(created_by=request.user))
        unit_id = request.query_params.get("unit_id")
        if unit_id:
            events = events.filter(unit_id=unit_id)
        events = events.order_by("-occurred_at")[:100]
        return Response(UnitEventReadSerializer(events, many=True).data)

    def post(self, request):
        serializer = UnitEventCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            event, created = record_unit_event(
                unit_id=data["unit_id"], center_id=data["center_id"],
                event_type=data["event_type"], created_by=request.user,
                occurred_at=data.get("occurred_at"), event_id=data["id"],
                note=data.get("note") or None,
            )
        except (OperationConflictError, UnitAlreadyLockedError) as error:
            return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
        except (InvalidMovementDataError, UnitNotAtOriginCenterError) as error:
            raise ValidationError({"detail": str(error)}) from error
        return Response(
            UnitEventReadSerializer(event).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Guide de réalisation des ajouts (21/11) : boucle RFID, marché, parcours, bilan
# ---------------------------------------------------------------------------


class RfidTagCreateView(APIView):
    """Pose une boucle RFID Vet'Tronic sur un animal (ajout 1). Droit : membre ou mandataire
    (déclarer) de l'élevage où se trouve l'animal."""

    def post(self, request):
        serializer = RfidTagCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        unit = TrackedUnit.objects.filter(pk=data["unit_id"]).first()
        if unit is None:
            raise NotFound("Animal introuvable.")
        if not user_can_access_center(request.user, unit.current_center_id, scope="declare"):
            raise PermissionDenied("Vous n'avez pas accès à cet élevage.")
        try:
            tag, created, warnings = bind_rfid_tag(
                unit_id=unit.pk, number=data["number"], read_mode=data["read_mode"],
                created_by=request.user, tag_id=data["id"], occurred_at=data.get("occurred_at"),
            )
        except OperationConflictError as error:
            return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
        except InvalidMovementDataError as error:
            raise ValidationError({"detail": str(error)}) from error
        return Response(
            {"id": tag.pk, "unit_id": tag.unit_id, "number": format_rfid(tag.number),
             "read_mode": tag.read_mode, "status": tag.status, "warnings": warnings},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class UnitRouteView(APIView):
    """Parcours d'un animal (ajout 4) : ses mouvements avec « Sûr » / « Probable ».
    Visible par qui voit sa fiche ; un élevage sans droit d'accès reste anonyme."""

    def get(self, request, unit_id):
        unit = TrackedUnit.objects.select_related("species").filter(pk=unit_id).first()
        if unit is None or not user_can_view_unit(request.user, unit):
            raise NotFound("Animal introuvable.")
        tag = active_rfid(unit.pk)
        return Response({
            "unit_id": unit.pk,
            "rfid": ({"number": format_rfid(tag.number), "read_mode": tag.read_mode}
                     if tag else None),
            "steps": unit_route(unit, request.user),
        })


class MarketScanView(APIView):
    """Un scan à l'Entrée ou à la Sortie d'un marché (ajouts 2 et 3) : membre du marché ou
    mandat « move » dessus. Ne bloque jamais : inconnu, déjà scanné ou refusé sont gardés."""

    permission_classes = [HasCenterAccess.for_scope("move")]

    def post(self, request, center_id):
        serializer = MarketScanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        market = Center.objects.filter(pk=center_id).first()
        if market is None:
            raise NotFound("Marché introuvable.")
        to_center = None
        if data.get("to_center_id"):
            to_center = Center.objects.filter(pk=data["to_center_id"], status="active").first()
            if to_center is None:
                raise ValidationError({"to_center_id": "Élevage acheteur introuvable."})
        try:
            body, created = record_market_scan(
                scan_id=data["id"], market=market, direction=data["direction"],
                code=data["code"], created_by=request.user, occurred_at=data.get("scanned_at"),
                latitude=data.get("latitude"), longitude=data.get("longitude"),
                position_accuracy_m=data.get("position_accuracy_m"),
                position_source=data.get("position_source", "none"),
                to_center=to_center, to_party_note=data.get("to_party_note"),
            )
        except OperationConflictError as error:
            return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
        except InvalidMovementDataError as error:
            raise ValidationError({"detail": str(error)}) from error
        return Response(body, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class MarketSummaryView(APIView):
    """Bilan du jour d'un marché (ajout 5), chiffres agrégés sans nom d'élevage. Droit :
    membre ou mandataire du marché, ou Autorité dont le périmètre contient le marché."""

    def get(self, request, center_id):
        market = Center.objects.filter(pk=center_id, center_type="market").first()
        allowed = market is not None and (
            user_can_access_center(request.user, market.pk)
            or user_covers_zone(request.user, market.zone_id, roles=("authority",))
        )
        if not allowed:
            raise NotFound("Marché introuvable.")
        raw_day = request.query_params.get("date")
        try:
            day = date.fromisoformat(raw_day) if raw_day else timezone.localdate()
        except ValueError as error:
            raise ValidationError({"date": "Date attendue au format AAAA-MM-JJ."}) from error
        return Response(market_summary(market, day))
