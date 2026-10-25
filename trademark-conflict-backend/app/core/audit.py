from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.models.audit_event import AuditEvent


def record_audit_event(
    db: Session,
    principal: Principal,
    action: str,
    resource_id: str | None = None,
    details: dict[str, object] | None = None,
) -> None:
    db.add(
        AuditEvent(
            tenant_id=principal.tenant_id,
            actor_id=principal.subject,
            action=action,
            resource_id=resource_id,
            details=json.dumps(details or {}, ensure_ascii=False),
        )
    )
