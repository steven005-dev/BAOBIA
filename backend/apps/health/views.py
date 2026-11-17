"""Routes health : catalogue, signalements, évaluation vétérinaire.

Droits et masquage côté serveur (health.services) ; écritures par services
(audit compris). Messages : vocabulaire officiel de la charte.
"""

from django.db import connection
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasRole, HasValidHabilitation
from apps.accounts.serializers import ErrorSerializer
from apps.identity.models import Center

from . import services
from .models import Disease, HealthReport, Symptom
from .serializers import (
    CatalogItemSerializer,
    ReportCreateSerializer,
    ReportOutSerializer,
    ReviewCreateSerializer,
    ReviewOutSerializer,
)

TAG_CATALOG = "Santé : catalogue"
TAG_REPORTS = "Santé : signalements"

REPORT_NOT_FOUND = "Signalement introuvable."
REPORT_SENT = "Signalement envoyé au vétérinaire."


class HealthView(APIView):
    """Vérification que le serveur et la base répondent (utilisée par l'infra)."""

    permission_classes = [AllowAny]

    @extend_schema(exclude=True)
    def get(self, request):
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        return Response({'status': 'ok', 'database': 'ok'})


# ---------------------------------------------------------------------------
# Présentation
# ---------------------------------------------------------------------------


def _catalog_item(item):
    return {"code": item.code, "label_fr": item.label_fr, "icon": getattr(item, "icon", None)}


def _report_queryset():
    return HealthReport.objects.select_related("center").prefetch_related(
        "symptoms", "subjects__unit__species", "reviews__disease", "reviews__created_by"
    )


def report_data(report, *, professional):
    """Réponse d'un signalement. `professional` (vétérinaire ou autorité de la zone)
    ajoute les décisions et la position ; un éleveur voit l'état de son signalement."""
    data = {
        "id": report.id,
        "center": {"id": report.center.id, "name": report.center.name,
                   "zone_id": report.center.zone_id},
        "report_kind": report.report_kind,
        "affected_count": report.affected_count,
        "self_severity": report.self_severity,
        "note": report.note,
        "status": report.status,
        "occurred_at": report.occurred_at,
        "created_at": report.created_at,
        "is_simulated": report.is_simulated,
        "symptoms": [_catalog_item(s) for s in report.symptoms.all()],
        "subjects": [
            {"unit_id": s.unit_id, "condition": s.condition,
             "species_code": s.unit.species.code, "local_name": s.unit.local_name}
            for s in report.subjects.all()
        ],
    }
    if professional:
        data["reviews"] = [
            {"id": r.id, "decision": r.decision,
             "disease": _catalog_item(r.disease) if r.disease else None,
             "note": r.note, "vet_name": r.created_by.full_name, "occurred_at": r.occurred_at}
            for r in sorted(report.reviews.all(), key=lambda r: r.occurred_at)
        ]
        data["position"] = (
            {"latitude": report.latitude, "longitude": report.longitude,
             "accuracy_m": report.position_accuracy_m, "source": report.position_source}
            if report.latitude is not None else None
        )
    return data


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------

SPECIES_PARAM = OpenApiParameter("species", str, description="Code d'espèce (ex. cattle).")


class SymptomListView(APIView):
    @extend_schema(tags=[TAG_CATALOG], summary="Symptômes à cocher",
                   parameters=[SPECIES_PARAM],
                   responses={200: CatalogItemSerializer(many=True)})
    def get(self, request):
        symptoms = Symptom.objects.filter(is_active=True).order_by("label_fr")
        species = request.query_params.get("species")
        if species:
            symptoms = symptoms.filter(species__code=species)
        return Response([_catalog_item(s) for s in symptoms])


class DiseaseListView(APIView):
    @extend_schema(tags=[TAG_CATALOG], summary="Maladies (choix du vétérinaire)",
                   parameters=[SPECIES_PARAM],
                   responses={200: CatalogItemSerializer(many=True)})
    def get(self, request):
        diseases = Disease.objects.filter(is_active=True).order_by("label_fr")
        species = request.query_params.get("species")
        if species:
            diseases = diseases.filter(species__code=species)
        return Response([_catalog_item(d) for d in diseases])


# ---------------------------------------------------------------------------
# Signalements
# ---------------------------------------------------------------------------


class ReportListCreateView(APIView):
    @extend_schema(
        tags=[TAG_REPORTS],
        summary="Signalements visibles",
        description=(
            "Éleveur : les siens et ceux de ses élevages. Vétérinaire ou autorité : ceux des "
            "zones couvertes, avec les décisions. Du plus récent au plus ancien."
        ),
        parameters=[
            OpenApiParameter("center_id", str, description="Un seul élevage."),
            OpenApiParameter("status", str, description="submitted, under_review, validated, "
                                                         "rejected, closed"),
        ],
        responses={200: ReportOutSerializer(many=True)},
    )
    def get(self, request):
        reports = _report_queryset().filter(
            pk__in=services.visible_reports(request.user).values("pk")
        )
        center_id = request.query_params.get("center_id")
        if center_id:
            reports = reports.filter(center_id=center_id)
        status_filter = request.query_params.get("status")
        if status_filter:
            reports = reports.filter(status=status_filter)
        reports = list(reports.order_by("-occurred_at")[:200])
        return Response([
            report_data(r, professional=services.is_professional_for(request.user, r))
            for r in reports
        ])

    @extend_schema(
        tags=[TAG_REPORTS],
        summary="Signaler un cas suspect",
        description=(
            "Opération hors ligne `health_report.submit`. `id` = UUID de l'opération. "
            "Rejouer la même opération renvoie 200 sans rien créer ; le même `id` avec un "
            "autre contenu renvoie 409 (« À vérifier »)."
        ),
        request=ReportCreateSerializer,
        responses={201: ReportOutSerializer, 200: ReportOutSerializer, 400: ErrorSerializer,
                   403: ErrorSerializer, 404: ErrorSerializer, 409: ErrorSerializer},
    )
    def post(self, request):
        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        center = Center.objects.filter(pk=data.pop("center_id")).first()
        if center is None:
            raise NotFound("Élevage introuvable.")
        try:
            report, created = services.submit_report(
                report_id=data.pop("id"), user=request.user, center=center, **data
            )
        except services.ReportConflict as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except services.HealthForbidden as exc:
            raise PermissionDenied(str(exc)) from exc
        except services.HealthError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        report = _report_queryset().get(pk=report.pk)
        body = report_data(report, professional=services.is_professional_for(request.user, report))
        body["message"] = REPORT_SENT
        return Response(body, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class ReportDetailView(APIView):
    @extend_schema(tags=[TAG_REPORTS], summary="Un signalement",
                   responses={200: ReportOutSerializer, 404: ErrorSerializer})
    def get(self, request, report_id):
        report = _report_queryset().filter(
            pk=report_id, pk__in=services.visible_reports(request.user).values("pk")
        ).first()
        if report is None:
            raise NotFound(REPORT_NOT_FOUND)
        return Response(
            report_data(report, professional=services.is_professional_for(request.user, report))
        )


class ReportReviewView(APIView):
    permission_classes = [HasRole("veterinarian"), HasValidHabilitation]

    @extend_schema(
        tags=[TAG_REPORTS],
        summary="Évaluer un signalement (vétérinaire habilité)",
        description=(
            "Décisions : request_info, retain_suspicion, raise_level2, validate_level3 "
            "(maladie obligatoire), dismiss (motif obligatoire), close. Seul un vétérinaire "
            "habilité dont la zone couvre l'élevage peut décider."
        ),
        request=ReviewCreateSerializer,
        responses={201: ReviewOutSerializer, 400: ErrorSerializer, 403: ErrorSerializer,
                   404: ErrorSerializer},
    )
    def post(self, request, report_id):
        report = HealthReport.objects.select_related("center").filter(pk=report_id).first()
        if report is None or not services.is_professional_for(request.user, report):
            raise NotFound(REPORT_NOT_FOUND)
        serializer = ReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        disease = None
        if data.get("disease_code"):
            disease = Disease.objects.filter(code=data["disease_code"], is_active=True).first()
            if disease is None:
                raise ValidationError({"detail": "Maladie inconnue."})
        try:
            review = services.review_report(
                report=report, vet=request.user, decision=data["decision"], disease=disease,
                note=data.get("note"), review_id=data.get("id"),
            )
        except services.HealthForbidden as exc:
            raise PermissionDenied(str(exc)) from exc
        except services.HealthError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response(
            {"id": review.id, "decision": review.decision,
             "disease": _catalog_item(disease) if disease else None, "note": review.note,
             "vet_name": request.user.full_name, "occurred_at": review.occurred_at,
             "report_status": HealthReport.objects.get(pk=report.pk).status},
            status=status.HTTP_201_CREATED,
        )
