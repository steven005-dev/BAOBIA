from django.urls import path

from .views import AlertDetailView, AlertListView, MapZonesView

app_name = "alerts"

urlpatterns = [
    path("alerts/", AlertListView.as_view(), name="alert-list"),
    path("alerts/<uuid:alert_id>/", AlertDetailView.as_view(), name="alert-detail"),
    path("map/zones/", MapZonesView.as_view(), name="map-zones"),
]
