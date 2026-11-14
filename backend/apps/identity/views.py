"""Routes identity : élevages (centres), animaux et lots, scan d'étiquette.

Aucune règle de droits écrite ici à la main : permissions d'accounts et fonctions
de identity.services. Les écritures passent par services (audit compris).
Messages : vocabulaire officiel de la charte (docs/BAOBIA_UI_GUIDELINES.md).
"""

from django.db.models import Sum
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasCenterAccess, HasRole
from apps.accounts.serializers import ErrorSerializer
from apps.core.models import Species
from apps.geo.models import Zone

from . import services
from .models import Center, CenterSpecies, IdentitySupport, TrackedUnit
from .serializers import (
    CenterCreateSerializer,
    CenterDetailSerializer,
    CenterListItemSerializer,
    LabelReplaceSerializer,
    ScanResultSerializer,
    UnitCreateSerializer,
    UnitListItemSerializer,
    UnitSerializer,
)

TAG_CENTERS = "Élevages"
TAG_UNITS = "Animaux et lots"
TAG_SCAN = "Scan"

UNIT_NOT_FOUND = "Animal introuvable. Vérifiez l'étiquette."
LABEL_NOT_RECOGNIZED = "Étiquette non reconnue. Essayez encore ou saisissez le code."
ID_TAKEN = "Cet identifiant est déjà utilisé."

SCAN_MESSAGES = {
    "found": "Animal retrouvé.",
    "replaced": "Étiquette remplacée. Voici l'animal qui la portait.",
    "lost": "Étiquette déclarée perdue.",
}


def _species_ref(species):
    return {"id": species.id, "code": species.code, "label_fr": species.label_fr,
            "tracking_mode": species.tracking_mode}


def _unit_queryset():
    return TrackedUnit.objects.select_related("species", "current_center", "animal", "lot")


def _label_codes(unit_ids):
    """Étiquette QR active de chaque unité, en une requête."""
    return dict(
        IdentitySupport.objects.filter(
            unit_id__in=unit_ids, support_type="qr_label", unbound_at__isnull=True
        ).values_list("unit_id", "label__short_code")
    )


def _unit_data(unit, label_code=None):
    animal = getattr(unit, "animal", None) if unit.kind == "animal" else None
    lot = getattr(unit, "lot", None) if unit.kind == "lot" else None
    if label_code is None:
        label = services.active_label(unit)
        label_code = label.short_code if label else None
    return {
        "id": unit.id,
        "kind": unit.kind,
        "species": _species_ref(unit.species),
        "local_name": unit.local_name,
        "life_status": unit.life_status,
        "current_center": (
            {"id": unit.current_center.id, "name": unit.current_center.name}
            if unit.current_center else None
        ),
        "label_code": label_code,
        "animal": (
            {"sex": animal.sex, "birth_date": animal.birth_date,
             "birth_date_precision": animal.birth_date_precision, "breed": animal.breed,
             "marks": animal.marks}
            if animal else None
        ),
        "lot": {"current_size": lot.current_size, "description": lot.description} if lot else None,
        "created_at": unit.created_at,
        "is_simulated": unit.is_simulated,
    }


# --------------------------------------------------------------------------- Centres

class CenterListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [HasRole("breeder", "trader")()]
        return super().get_permissions()

    @extend_schema(
        tags=[TAG_CENTERS],
        summary="Mes élevages",
        description="Élevages auxquels l'utilisateur connecté a accès (membre ou mandat actif).",
        responses={200: CenterListItemSerializer(many=True), 401: ErrorSerializer},
    )
    def get(self, request):
        centers = services.accessible_centers(request.user)
        return Response(CenterListItemSerializer(
            [{k: c[k] for k in ("id", "name", "center_type", "zone_id", "access")} for c in centers],
            many=True,
        ).data)

    @extend_schema(
        tags=[TAG_CENTERS],
        summary="Ajouter un élevage",
        description=(
            "Réservé aux rôles éleveur et commerçant. L'utilisateur devient le détenteur "
            "(holder). Si `id` est fourni et existe déjà pour cet utilisateur, l'élevage "
            "existant est renvoyé (200) : rejouer l'envoi hors ligne est sans effet."
        ),
        request=CenterCreateSerializer,
        responses={201: CenterDetailSerializer, 200: CenterDetailSerializer,
                   400: ErrorSerializer, 403: ErrorSerializer, 409: ErrorSerializer},
    )
    def post(self, request):
        serializer = CenterCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if "id" in data:
            existing = Center.objects.filter(pk=data["id"]).first()
            if existing is not None:
                if existing.created_by_id != request.user.id:
                    return Response({"detail": ID_TAKEN}, status=status.HTTP_409_CONFLICT)
                return Response(CenterDetailView.detail_data(existing))

        zone = Zone.objects.filter(pk=data["zone_id"]).first()
        if zone is None:
            raise ValidationError({"zone_id": ["Zone inconnue."]})
        species = list(Species.objects.filter(pk__in=data["species_ids"], is_active=True))
        if len(species) != len(set(data["species_ids"])):
            raise ValidationError({"species_ids": ["Espèce inconnue."]})

        center = services.create_center(
            name=data["name"], zone=zone, center_type=data["center_type"],
            created_by=request.user, holder=request.user, species=species,
            center_id=data.get("id"),
        )
        return Response(CenterDetailView.detail_data(center), status=status.HTTP_201_CREATED)


class CenterDetailView(APIView):
    permission_classes = [HasCenterAccess]

    @staticmethod
    def detail_data(center):
        units = TrackedUnit.objects.filter(current_center=center, life_status="active")
        animals = units.filter(kind="animal").count()
        lots = units.filter(kind="lot")
        lot_heads = lots.aggregate(total=Sum("lot__current_size"))["total"] or 0
        species = Species.objects.filter(
            pk__in=CenterSpecies.objects.filter(center=center).values("species_id")
        ).order_by("label_fr")
        return CenterDetailSerializer({
            "id": center.id,
            "name": center.name,
            "center_type": center.center_type,
            "status": center.status,
            "zone": {"id": center.zone.id, "name": center.zone.name},
            "species": [_species_ref(sp) for sp in species],
            "animals_count": animals,
            "lots_count": lots.count(),
            "heads_count": animals + lot_heads,
            "is_simulated": center.is_simulated,
        }).data

    @extend_schema(
        tags=[TAG_CENTERS],
        summary="Fiche d'un élevage",
        description="Membres et mandataires actifs de l'élevage uniquement.",
        responses={200: CenterDetailSerializer, 403: ErrorSerializer, 404: ErrorSerializer},
    )
    def get(self, request, center_id):
        center = Center.objects.select_related("zone").filter(pk=center_id).first()
        if center is None:
            raise NotFound("Élevage introuvable.")
        return Response(self.detail_data(center))


class CenterUnitsView(APIView):
    permission_classes = [HasCenterAccess]

    @extend_schema(
        tags=[TAG_CENTERS],
        summary="Animaux et lots présents dans un élevage",
        description="Unités actives dont le centre courant est cet élevage. Membres et mandataires uniquement.",
        responses={200: UnitListItemSerializer(many=True), 403: ErrorSerializer},
    )
    def get(self, request, center_id):
        units = list(
            _unit_queryset().filter(current_center_id=center_id, life_status="active")
            .order_by("-created_at")
        )
        codes = _label_codes([u.id for u in units])
        return Response(UnitListItemSerializer([
            {
                "id": u.id,
                "kind": u.kind,
                "species": _species_ref(u.species),
                "local_name": u.local_name,
                "life_status": u.life_status,
                "label_code": codes.get(u.id),
                "size": u.lot.current_size if u.kind == "lot" else 1,
            }
            for u in units
        ], many=True).data)


# --------------------------------------------------------------------------- Unités

class UnitCreateView(APIView):
    # Le centre vient du corps (center_id) ; un mandat doit donner le droit "declare".
    permission_classes = [HasCenterAccess.for_scope("declare")]

    @extend_schema(
        tags=[TAG_UNITS],
        summary="Ajouter un animal ou un lot",
        description=(
            "Enregistre l'unité dans l'élevage `center_id` et pose l'étiquette `label_code` "
            "si elle est donnée. Si `id` existe déjà pour cet utilisateur, l'unité existante "
            "est renvoyée (200) : rejouer l'envoi hors ligne est sans effet."
        ),
        request=UnitCreateSerializer,
        responses={201: UnitSerializer, 200: UnitSerializer, 400: ErrorSerializer,
                   403: ErrorSerializer, 409: ErrorSerializer},
    )
    def post(self, request):
        serializer = UnitCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if "id" in data:
            existing = _unit_queryset().filter(pk=data["id"]).first()
            if existing is not None:
                if existing.created_by_id != request.user.id:
                    return Response({"detail": ID_TAKEN}, status=status.HTTP_409_CONFLICT)
                return Response(UnitSerializer(_unit_data(existing)).data)

        center = Center.objects.filter(pk=data["center_id"], status="active").first()
        if center is None:
            raise ValidationError({"center_id": ["Élevage introuvable ou fermé."]})
        species = Species.objects.filter(pk=data["species_id"], is_active=True).first()
        if species is None:
            raise ValidationError({"species_id": ["Espèce inconnue."]})

        try:
            label = (
                services.label_for_registration(data["label_code"], center)
                if data.get("label_code") else None
            )
            common = {
                "species": species, "center": center, "created_by": request.user,
                "unit_id": data.get("id"), "local_name": data.get("local_name") or None,
                "label": label,
            }
            if data["kind"] == "animal":
                unit = services.register_animal(
                    **common, sex=data["sex"], birth_date=data.get("birth_date"),
                    birth_date_precision=data.get("birth_date_precision"),
                    breed=data.get("breed") or None, marks=data.get("marks") or None,
                )
            else:
                unit = services.register_lot(
                    **common, size=data["size"], description=data.get("description") or None,
                )
        except services.IdentityError as exc:
            raise ValidationError({"detail": str(exc)}) from exc

        unit = _unit_queryset().get(pk=unit.pk)
        return Response(UnitSerializer(_unit_data(unit)).data, status=status.HTTP_201_CREATED)


class UnitDetailView(APIView):
    @extend_schema(
        tags=[TAG_UNITS],
        summary="Fiche d'un animal ou d'un lot",
        description=(
            "Visible par les membres ou mandataires de l'élevage où se trouve l'unité, et par "
            "les vétérinaires ou autorités dont la zone couvre cet élevage. Sinon 404 "
            "(on ne révèle pas qu'elle existe)."
        ),
        responses={200: UnitSerializer, 404: ErrorSerializer},
    )
    def get(self, request, unit_id):
        unit = _unit_queryset().filter(pk=unit_id).first()
        if unit is None or not services.user_can_view_unit(request.user, unit):
            raise NotFound(UNIT_NOT_FOUND)
        return Response(UnitSerializer(_unit_data(unit)).data)


class UnitLabelView(APIView):
    @extend_schema(
        tags=[TAG_UNITS],
        summary="Remplacer l'étiquette d'un animal ou d'un lot",
        description=(
            "Membres et mandataires (droit « declare ») de l'élevage où se trouve l'unité. "
            "L'ancienne étiquette est retirée (perdue ou désactivée), la nouvelle posée, dans "
            "une transaction ; l'historique est conservé. 404 si l'unité n'est pas visible."
        ),
        request=LabelReplaceSerializer,
        responses={200: UnitSerializer, 400: ErrorSerializer, 403: ErrorSerializer,
                   404: ErrorSerializer},
    )
    def post(self, request, unit_id):
        unit = _unit_queryset().filter(pk=unit_id).first()
        if unit is None or not services.user_can_view_unit(request.user, unit):
            raise NotFound(UNIT_NOT_FOUND)
        if not services.user_can_access_center(request.user, unit.current_center_id, scope="declare"):
            raise PermissionDenied("Vous n'avez pas accès à cet élevage.")
        serializer = LabelReplaceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            label = services.label_for_registration(data["label_code"], unit.current_center)
            services.replace_label(unit, label, request.user, reason=data["reason"])
        except services.IdentityError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        unit = _unit_queryset().get(pk=unit.pk)
        return Response(UnitSerializer(_unit_data(unit)).data)


# --------------------------------------------------------------------------- Scan

class ScanView(APIView):
    @extend_schema(
        tags=[TAG_SCAN],
        summary="Scanner une étiquette",
        description=(
            "Résout le code d'une étiquette (QR ou saisi : espaces et tirets acceptés). "
            "Vue complète si l'utilisateur peut voir la fiche ; sinon vue réduite (espèce "
            "seulement, aucun élevage). 400 si le code est mal formé ou son caractère de "
            "contrôle faux ; 404 si aucune étiquette ou étiquette non posée. Lecture seule."
        ),
        parameters=[OpenApiParameter("code", str, OpenApiParameter.PATH,
                                     description="Code court de 9 caractères.")],
        responses={200: ScanResultSerializer, 400: ErrorSerializer, 404: ErrorSerializer},
    )
    def get(self, request, code):
        result, label, unit = services.scan_label(code)
        if result == "invalid":
            raise ValidationError({"detail": LABEL_NOT_RECOGNIZED})
        if result == "unknown":
            raise NotFound(UNIT_NOT_FOUND)
        if result == "not_bound":
            raise NotFound("Cette étiquette n'est posée sur aucun animal.")

        unit = _unit_queryset().get(pk=unit.pk)
        full = services.user_can_view_unit(request.user, unit)
        return Response(ScanResultSerializer({
            "result": result,
            "message": SCAN_MESSAGES[result],
            "label_code": label.short_code,
            "full_access": full,
            "unit": _unit_data(unit) if full else None,
            "species": _species_ref(unit.species),
        }).data)

