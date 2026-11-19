from django.apps import AppConfig


class AlertsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.alerts'

    def ready(self):
        # alerts répond aux évaluations de health (health ne connaît pas alerts).
        from apps.health.signals import report_reviewed

        from .services import handle_report_review

        def _on_report_reviewed(sender, report, review, **kwargs):
            handle_report_review(report, review)

        report_reviewed.connect(_on_report_reviewed, dispatch_uid="alerts.handle_report_review",
                                weak=False)
