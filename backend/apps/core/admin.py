from django.contrib import admin

from .models import Species


@admin.register(Species)
class SpeciesAdmin(admin.ModelAdmin):
    list_display = ("label_fr", "code", "tracking_mode", "is_active")
    list_filter = ("tracking_mode", "is_active")
    search_fields = ("code", "label_fr")

    def has_delete_permission(self, request, obj=None):
        return False  # aucune suppression physique : désactiver (is_active)
