"""Administration des comptes (équipe technique). Les mots de passe ne s'y modifient pas :
`python manage.py changepassword <téléphone>`. Les rôles, zones et habilitations s'y
règlent pour préparer une démonstration ; en production, passer par accounts.services."""

from django.contrib import admin

from apps.core.readonly_admin import ReadOnlyAdmin

from .models import Device, Habilitation, Mandate, Membership, Organization, Role, User


class NoDeleteAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        return False  # désactiver ou terminer (ends_at), jamais supprimer


@admin.register(User)
class UserAdmin(NoDeleteAdmin):
    list_display = ("phone", "full_name", "is_active", "is_simulated", "is_staff")
    list_filter = ("is_active", "is_simulated", "is_staff")
    search_fields = ("phone", "full_name")
    exclude = ("password", "user_permissions", "groups")
    readonly_fields = ("last_login", "created_at", "is_superuser")

    def has_add_permission(self, request, obj=None):
        return False  # comptes créés par seed, createsuperuser ou l'application


@admin.register(Role)
class RoleAdmin(NoDeleteAdmin):
    list_display = ("code", "label_fr")


@admin.register(Organization)
class OrganizationAdmin(NoDeleteAdmin):
    list_display = ("name", "kind", "zone", "is_active", "is_simulated")
    list_filter = ("kind", "is_active")


@admin.register(Membership)
class MembershipAdmin(NoDeleteAdmin):
    list_display = ("user", "role", "zone", "organization", "starts_at", "ends_at")
    list_filter = ("role", "zone")
    search_fields = ("user__phone", "user__full_name")
    autocomplete_fields = ("user",)


@admin.register(Habilitation)
class HabilitationAdmin(NoDeleteAdmin):
    list_display = ("user", "kind", "reference_number", "status", "valid_from", "valid_to")
    list_filter = ("status", "kind")
    search_fields = ("user__phone", "reference_number")
    autocomplete_fields = ("user", "verified_by")


@admin.register(Mandate)
class MandateAdmin(NoDeleteAdmin):
    list_display = ("agent_user", "granted_by", "scope", "starts_at", "ends_at", "revoked_at")
    list_filter = ("scope",)


@admin.register(Device)
class DeviceAdmin(ReadOnlyAdmin):
    list_display = ("user", "platform", "label", "registered_at", "revoked_at")
