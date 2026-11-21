class TraceabilityError(Exception):
    """Exception de base pour les erreurs du module de traçabilité."""
    pass


class UnitAlreadyLockedError(TraceabilityError):
    """Levée lorsqu'une unité est déjà engagée dans un mouvement non terminé."""
    pass


class UnitNotAtOriginCenterError(TraceabilityError):
    """Levée lorsqu'une unité ne se trouve pas dans le centre expéditeur indiqué."""
    pass


class InvalidMovementDataError(TraceabilityError):
    """Levée lorsque les données fournies pour le mouvement sont invalides."""
    pass


class InvalidConfirmationCodeError(TraceabilityError):
    """Levée lorsque le code de réception est invalide, expiré ou déjà utilisé."""
    pass


class OperationConflictError(TraceabilityError):
    """Levée lorsqu'un identifiant d'opération est rejoué avec un autre contenu (409)."""
    pass


class MovementNotReceivableError(TraceabilityError):
    """Levée lorsque le mouvement ne peut pas être reçu par cet élevage."""
    pass
