from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import Principal, require_roles
from app.db.database import get_db
from app.models.audit_event import AuditEvent

router = APIRouter(prefix="/api/audit", tags=["Audit"])


@router.get("")
def get_audit_events(
    limit: int = Query(default=100, ge=1, le=500),
    before: datetime | None = None,
    principal: Principal = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    statement = (
        select(AuditEvent)
        .where(AuditEvent.tenant_id == principal.tenant_id)
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .limit(limit)
    )
    if before is not None:
        statement = statement.where(AuditEvent.created_at < before)
    events = db.execute(statement).scalars().all()
    return [
        {
            "id": event.id,
            "actor_id": event.actor_id,
            "action": event.action,
            "resource_id": event.resource_id,
            "details": event.details,
            "created_at": event.created_at,
        }
        for event in events
    ]
