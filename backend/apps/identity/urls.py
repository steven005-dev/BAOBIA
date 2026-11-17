from django.urls import path

from .views import (
    CenterDetailView,
    CenterListCreateView,
    CenterUnitsView,
    ScanView,
    UnitCreateView,
    UnitDetailView,
)

urlpatterns = [
    path("centers/", CenterListCreateView.as_view(), name="center-list"),
    path("centers/<uuid:center_id>/", CenterDetailView.as_view(), name="center-detail"),
    path("centers/<uuid:center_id>/units/", CenterUnitsView.as_view(), name="center-units"),
    path("units/", UnitCreateView.as_view(), name="unit-create"),
    path("units/<uuid:unit_id>/", UnitDetailView.as_view(), name="unit-detail"),
    path("scan/<str:code>/", ScanView.as_view(), name="scan"),
]
