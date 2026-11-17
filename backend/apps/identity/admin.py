"""Identity en consultation seule : les écritures passent par identity.services
(centre courant, étiquettes, journal d'audit). Seuls le nom et le statut d'un centre
se corrigent ici."""

from django.contrib import admin

from apps.core.readonly_admin import ReadOnlyAdmin

from .models import (
    Center,
    CenterMember,
    IdentitySupport,
    IdentityVerification,
    Label,
    LabelBatch,
    TrackedUnit,
)


@admin.register(Center)
class CenterAdmin(admin.ModelAdmin):
    list_display = ("name", "center_type", "zone", "status", "is_simulated")
    list_filter = ("center_type", "status", "zone")
    search_fields = ("name",)
    fields = ("name", "status")

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CenterMember)
class CenterMemberAdmin(ReadOnlyAdmin):
    list_display = ("center", "user", "member_role", "starts_at", "ends_at")
    list_filter = ("member_role",)


@admin.register(TrackedUnit)
class TrackedUnitAdmin(ReadOnlyAdmin):
    list_display = ("id", "kind", "species", "current_center", "life_status", "is_simulated")
    list_filter = ("kind", "species", "life_status")
    search_fields = ("id", "local_name")


@admin.register(LabelBatch)
class LabelBatchAdmin(ReadOnlyAdmin):
    list_display = ("id", "quantity", "created_by", "created_at", "note")


@admin.register(Label)
class LabelAdmin(ReadOnlyAdmin):
    list_display = ("short_code", "status", "issued_to_center", "batch")
    list_filter = ("status",)
    search_fields = ("short_code",)


@admin.register(IdentitySupport)
class IdentitySupportAdmin(ReadOnlyAdmin):
    list_display = ("unit", "support_type", "label", "bound_at", "unbound_at", "unbound_reason")


@admin.register(IdentityVerification)
class IdentityVerificationAdmin(ReadOnlyAdmin):
    list_display = ("unit", "method", "result", "occurred_at", "position_source", "created_by")
    list_filter = ("result", "method")
