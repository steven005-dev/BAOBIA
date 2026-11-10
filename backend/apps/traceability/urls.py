from django.urls import path
from apps.traceability.views import MovementDetailView, MovementListCreateView

app_name = "traceability"

urlpatterns = [
    path("movements/", MovementListCreateView.as_view(), name="movement-list-create"),
    path("movements/<uuid:pk>/", MovementDetailView.as_view(), name="movement-detail"),
]
