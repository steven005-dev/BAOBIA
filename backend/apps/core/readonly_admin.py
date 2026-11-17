"""Administration Django (équipe technique uniquement, jamais un rôle métier).

ReadOnlyAdmin : consultation seule. À utiliser pour les événements (ajout seul), le
journal d'audit et toute table dont les colonnes sont écrites par services.py :
modifier ces lignes à la main contournerait les règles et le journal d'audit.
"""

from django.contrib import admin


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
