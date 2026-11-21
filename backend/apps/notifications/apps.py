from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notifications'

    def ready(self):
        """Messages à tous les acteurs (21/11) sans toucher au code des autres modules :
        - signalement examiné : signal health.report_reviewed ;
        - chaque étape d'un mouvement : création d'un MovementStatusEvent (traceability)."""
        from django.db.models.signals import post_save

        from apps.health.signals import report_reviewed
        from apps.traceability.models import MovementStatusEvent

        from . import services

        def _on_report_reviewed(sender, report, review, **kwargs):
            services.on_report_reviewed(report, review)

        def _on_movement_status(sender, instance, created, **kwargs):
            if created:
                services.on_movement_status(instance)

        report_reviewed.connect(_on_report_reviewed, dispatch_uid="notifications.report_reviewed",
                                weak=False)
        post_save.connect(_on_movement_status, sender=MovementStatusEvent,
                          dispatch_uid="notifications.movement_status", weak=False)
