from django.urls import path

from .views import (
    DiseaseListView,
    ReportDetailView,
    ReportListCreateView,
    ReportReviewView,
    SymptomListView,
)

app_name = "health"

urlpatterns = [
    path("symptoms/", SymptomListView.as_view(), name="symptom-list"),
    path("diseases/", DiseaseListView.as_view(), name="disease-list"),
    path("health-reports/", ReportListCreateView.as_view(), name="report-list-create"),
    path("health-reports/<uuid:report_id>/", ReportDetailView.as_view(), name="report-detail"),
    path("health-reports/<uuid:report_id>/review/", ReportReviewView.as_view(),
         name="report-review"),
]
