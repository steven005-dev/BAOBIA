from django.contrib import admin

from apps.core.readonly_admin import ReadOnlyAdmin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(ReadOnlyAdmin):
    """Journal inaltérable : consultation seule (la base refuse aussi UPDATE et DELETE)."""

    list_display = ("at", "action", "actor_user", "entity_table", "entity_id")
    list_filter = ("action", "entity_table")
    search_fields = ("action", "entity_id", "actor_user__phone")
    date_hierarchy = "at"
