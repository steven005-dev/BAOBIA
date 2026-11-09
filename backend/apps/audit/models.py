from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    at = models.DateTimeField(auto_now_add=True)
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT
    )
    device = models.ForeignKey(
        "accounts.Device", null=True, blank=True, on_delete=models.PROTECT
    )
    action = models.CharField(max_length=40)
    entity_table = models.CharField(max_length=40)
    entity_id = models.UUIDField(null=True, blank=True)
    details = models.JSONField(default=dict)
    prev_hash = models.CharField(max_length=64, null=True, blank=True)
    hash = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        db_table = "audit_log"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise RuntimeError("Le journal d'audit ne se modifie pas.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Le journal d'audit ne se supprime pas.")
