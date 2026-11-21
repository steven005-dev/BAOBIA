from django.urls import path
from apps.traceability.views import (
    DestinationShareCodeView,
    MarketEntryView,
    MarketScanView,
    MarketSummaryView,
    RfidTagCreateView,
    UnitRouteView,
    MarketExitView,
    MovementCancelView,
    MovementConfirmView,
    MovementContestView,
    MovementDetailView,
    MovementListCreateView,
    MovementRefuseView,
    UnitEventListCreateView,
)

app_name = "traceability"

urlpatterns = [
    path("movements/destination-code/", DestinationShareCodeView.as_view(), name="movement-destination-code"),
    path("movements/", MovementListCreateView.as_view(), name="movement-list-create"),
    path("movements/<uuid:pk>/confirm/", MovementConfirmView.as_view(), name="movement-confirm"),
    path("movements/<uuid:pk>/refuse/", MovementRefuseView.as_view(), name="movement-refuse"),
    path("movements/<uuid:pk>/cancel/", MovementCancelView.as_view(), name="movement-cancel"),
    path("movements/<uuid:pk>/contest/", MovementContestView.as_view(), name="movement-contest"),
    path("movements/<uuid:pk>/", MovementDetailView.as_view(), name="movement-detail"),
    path("unit-events/", UnitEventListCreateView.as_view(), name="unit-event-list-create"),
    path("market/entries/", MarketEntryView.as_view(), name="market-entry"),
    path("market/exits/", MarketExitView.as_view(), name="market-exit"),
    path("markets/<uuid:center_id>/scans/", MarketScanView.as_view(), name="market-scan"),
    path("markets/<uuid:center_id>/summary/", MarketSummaryView.as_view(), name="market-summary"),
    path("rfid-tags/", RfidTagCreateView.as_view(), name="rfid-tag-create"),
    path("units/<uuid:unit_id>/route/", UnitRouteView.as_view(), name="unit-route"),
]
