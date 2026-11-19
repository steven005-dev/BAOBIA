"""Signaux publics du module health.

`report_reviewed` est envoyé par health.services.review_report, DANS la
transaction de l'évaluation. Le module alerts s'y abonne (alerts dépend de
health, jamais l'inverse) pour créer ou faire évoluer l'alerte.

Arguments envoyés : sender=HealthReport, report, review.
"""

from django.dispatch import Signal

report_reviewed = Signal()
