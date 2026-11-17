from django.urls import path
from apps.traceability.views import (
    DestinationShareCodeView,
    MovementConfirmView,
    MovementDetailView,
    MovementListCreateView,
)

app_name = "traceability"

urlpatterns = [
    path("movements/destination-code/", DestinationShareCodeView.as_view(), name="movement-destination-code"),
    path("movements/", MovementListCreateView.as_view(), name="movement-list-create"),
    path("movements/<uuid:pk>/confirm/", MovementConfirmView.as_view(), name="movement-confirm"),
    path("movements/<uuid:pk>/", MovementDetailView.as_view(), name="movement-detail"),
]
