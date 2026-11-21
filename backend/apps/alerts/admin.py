from django.contrib import admin

from .models import Alert, AlertEvent, AlertExposure, DiseaseRule


@admin.register(DiseaseRule)
class DiseaseRuleAdmin(admin.ModelAdmin):
    """Règles versionnées : une règle utilisée par une alerte est refusée en
    modification par la base ; créer alors la version suivante."""

    list_display = ("disease", "species", "version", "lookback_days", "lookforward_days",
                    "max_depth", "min_zone_effectif", "valid_from", "valid_to")
    list_filter = ("disease",)


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Alert)
class AlertAdmin(ReadOnlyAdmin):
    list_display = ("id", "level", "status", "trigger_kind", "disease", "zone", "opened_at",
                    "is_simulated")
    list_filter = ("level", "status", "trigger_kind")


@admin.register(AlertExposure)
class AlertExposureAdmin(ReadOnlyAdmin):
    list_display = ("alert", "center", "exposure_status", "depth", "last_contact_at", "run_id")
    list_filter = ("exposure_status",)


@admin.register(AlertEvent)
class AlertEventAdmin(ReadOnlyAdmin):
    list_display = ("alert", "event_type", "occurred_at", "created_by")
    list_filter = ("event_type",)
