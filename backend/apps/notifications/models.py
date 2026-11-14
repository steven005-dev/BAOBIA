from django.conf import settings
from django.db import models

from apps.core.models import UUIDModel


class Notification(UUIDModel):
    """Message neutre envoyé à un utilisateur (spec section 6, table `notification`).

    Jamais l'identité de l'élevage d'origine : le texte vient d'un gabarit
    (`message_code`, vocabulaire officiel) et `params` est contrôlé par services.py.
    """

    class Channel(models.TextChoices):
        IN_APP = "in_app"
        SMS = "sms"
        PUSH = "push"

    class Status(models.TextChoices):
        PENDING = "pending"
        SENT = "sent"
        READ = "read"
        FAILED = "failed"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    # Spec : FK alert NULL. La table `alert` (application alerts, Yéo) n'existe pas encore :
    # identifiant seul en attendant ; une migration le changera en ForeignKey("alerts.Alert")
    # quand le modèle sera fusionné (même colonne alert_id, aucune donnée à migrer).
    alert_id = models.UUIDField(null=True, blank=True, db_index=True)
    kind = models.CharField(max_length=24)
    message_code = models.CharField(max_length=40)
    params = models.JSONField(default=dict, blank=True)
    channel = models.CharField(max_length=8, choices=Channel.choices, default=Channel.IN_APP)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PENDING)
    dedup_key = models.CharField(max_length=80, null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notification"
        indexes = [
            models.Index(fields=("user", "status", "-created_at"), name="idx_notification_user_status"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(channel__in=("in_app", "sms", "push")),
                name="chk_notification_channel",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=("pending", "sent", "read", "failed")),
                name="chk_notification_status",
            ),
        ]
