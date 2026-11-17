from django.contrib import admin

from .models import Disease, HealthEvent, HealthReport, HealthReportReview, Symptom


@admin.register(Disease)
class DiseaseAdmin(admin.ModelAdmin):
    list_display = ("code", "label_fr", "is_notifiable", "is_active")
    search_fields = ("code", "label_fr")


@admin.register(Symptom)
class SymptomAdmin(admin.ModelAdmin):
    list_display = ("code", "label_fr", "icon", "is_active")
    search_fields = ("code", "label_fr")


class ReadOnlyAdmin(admin.ModelAdmin):
    """Consultation seule : signalements et événements s'écrivent par health.services."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HealthReport)
class HealthReportAdmin(ReadOnlyAdmin):
    list_display = ("id", "center", "report_kind", "affected_count", "status", "occurred_at",
                    "is_simulated")
    list_filter = ("status", "report_kind", "is_simulated")


@admin.register(HealthReportReview)
class HealthReportReviewAdmin(ReadOnlyAdmin):
    list_display = ("id", "report", "decision", "created_by", "occurred_at")
    list_filter = ("decision",)


@admin.register(HealthEvent)
class HealthEventAdmin(ReadOnlyAdmin):
    list_display = ("id", "unit", "event_type", "disease", "occurred_at")
    list_filter = ("event_type",)
