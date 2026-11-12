from fastapi import Request, Response
from sqlalchemy.orm import Session

from src.schemas.score import ScoreCreateRequest
from src.services import audit_service, score_service


def list_batches(db: Session, limit: int = 20) -> dict:
    return {"items": score_service.list_batches(db, limit)}


def get_batch(db: Session, batch_id: int, include_results: bool = True) -> dict:
    batch = score_service.get_batch(db, batch_id)
    return score_service.batch_payload(batch, include_results=include_results)


def active_batch(db: Session) -> dict:
    """当前现行策略；没有任何发布时 active 为 None。"""
    return {"active": score_service.batch_payload(score_service.active_batch(db))}


def create_batch(db: Session, payload: ScoreCreateRequest, actor: dict, request: Request) -> dict:
    batch, reused = score_service.create_score_batch(
        db,
        actor_email=actor["email"],
        threshold=payload.threshold,
        budget_total=payload.budget_total,
        cost_per_account=payload.cost_per_account,
        retention_lift=payload.retention_lift,
        model_run_id=payload.model_run_id,
    )
    audit_service.record(
        db,
        actor_email=actor["email"],
        actor_role=actor["role"],
        action="score.reuse" if reused else "score.create",
        resource_type="score_batch",
        resource_id=str(batch.id),
        detail={
            "reused": reused,
            "batch_no": batch.batch_no,
            "lifecycle": batch.lifecycle,
            "threshold": batch.threshold,
            "budget_total": batch.budget_total,
            "selected_count": batch.selected_count,
        },
        ip=request.client.host if request.client else "",
        request_id=getattr(request.state, "request_id", ""),
    )
    payload_out = score_service.batch_payload(batch)
    payload_out["reused"] = reused
    return payload_out


def publish(db: Session, batch_id: int, actor: dict, request: Request) -> dict:
    result = score_service.publish_batch(db, batch_id, actor["email"])
    active = result["active"]
    audit_service.record(
        db,
        actor_email=actor["email"],
        actor_role=actor["role"],
        action="score.publish",
        resource_type="score_batch",
        resource_id=str(batch_id),
        detail={
            "switched": result["switched"],
            "reason": result["reason"],
            "policy_version": active.get("policy_version"),
            "threshold": active.get("threshold"),
            "previous_batch_id": result["previous"]["id"] if result["previous"] else None,
        },
        ip=request.client.host if request.client else "",
        request_id=getattr(request.state, "request_id", ""),
    )
    return result


def diff(db: Session, batch_id: int) -> dict:
    return score_service.policy_diff(db, batch_id)


def export_active(db: Session, actor: dict) -> Response:
    owner_email = actor["email"] if actor["role"] == "csm" else None
    csv_text, filename = score_service.export_csv(db, None, owner_email)
    return Response(
        content=csv_text.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def export(db: Session, batch_id: int, actor: dict) -> Response:
    owner_email = actor["email"] if actor["role"] == "csm" else None
    csv_text, filename = score_service.export_csv(db, batch_id, owner_email)
    return Response(
        content=csv_text.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
