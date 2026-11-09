from .models import AuditLog


def record_event(
    action,
    *,
    actor_user=None,
    entity_table="app_user",
    entity_id=None,
    details=None,
    device=None,
):
    """Append an audit event; callers must never put credentials in details."""
    return AuditLog.objects.create(
        action=action,
        actor_user=actor_user,
        device=device,
        entity_table=entity_table,
        entity_id=entity_id,
        details=details or {},
    )
