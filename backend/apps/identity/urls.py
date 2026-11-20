from django.urls import path

from .views import (
    BreederRegisterView,
    CenterDetailView,
    CenterLabelsView,
    CenterListCreateView,
    CenterUnitsView,
    LabelBatchView,
    ScanView,
    UnitCreateView,
    UnitDetailView,
    UnitLabelView,
    UnitVerificationView,
    ZoneListView,
)

urlpatterns = [
    path("breeders/", BreederRegisterView.as_view(), name="breeder-register"),
    path("centers/", CenterListCreateView.as_view(), name="center-list"),
    path("centers/<uuid:center_id>/", CenterDetailView.as_view(), name="center-detail"),
    path("centers/zones/", ZoneListView.as_view(), name="center-zones"),
    path("label-batches/", LabelBatchView.as_view(), name="label-batch-create"),
    path("centers/<uuid:center_id>/labels/", CenterLabelsView.as_view(), name="center-labels"),
    path("centers/<uuid:center_id>/units/", CenterUnitsView.as_view(), name="center-units"),
    path("units/", UnitCreateView.as_view(), name="unit-create"),
    path("units/<uuid:unit_id>/", UnitDetailView.as_view(), name="unit-detail"),
    path("units/<uuid:unit_id>/label/", UnitLabelView.as_view(), name="unit-label"),
    path("units/<uuid:unit_id>/verifications/", UnitVerificationView.as_view(), name="unit-verifications"),
    path("scan/<str:code>/", ScanView.as_view(), name="scan"),
]
