from django.urls import path
from apps.traceability.views import (
    DestinationShareCodeView,
    MarketEntryView,
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
]
