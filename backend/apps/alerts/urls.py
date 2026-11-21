from django.urls import path

from .views import AlertDetailView, AlertListView, MapFlowsView, MapZonesView

app_name = "alerts"

urlpatterns = [
    path("alerts/", AlertListView.as_view(), name="alert-list"),
    path("alerts/<uuid:alert_id>/", AlertDetailView.as_view(), name="alert-detail"),
    path("map/zones/", MapZonesView.as_view(), name="map-zones"),
    path("map/flows/", MapFlowsView.as_view(), name="map-flows"),
]
