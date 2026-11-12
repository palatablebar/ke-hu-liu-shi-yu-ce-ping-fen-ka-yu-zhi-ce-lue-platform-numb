from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.audit_log import AuditLog


def record(
    db: Session,
    *,
    actor_email: str,
    actor_role: str,
    action: str,
    resource_type: str = "",
    resource_id: str = "",
    detail: dict | None = None,
    ip: str = "",
    request_id: str = "",
) -> None:
    db.add(
        AuditLog(
            actor_email=actor_email,
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            detail=detail or {},
            ip=ip,
            request_id=request_id,
        )
    )
    db.commit()


def list_logs(db: Session, limit: int = 100) -> list[dict]:
    rows = db.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)).scalars().all()
    return [
        {
            "id": row.id,
            "actor_email": row.actor_email,
            "actor_role": row.actor_role,
            "action": row.action,
            "resource_type": row.resource_type,
            "resource_id": row.resource_id,
            "detail": row.detail,
            "created_at": row.created_at.isoformat(sep=" ", timespec="seconds") if row.created_at else None,
        }
        for row in rows
    ]
