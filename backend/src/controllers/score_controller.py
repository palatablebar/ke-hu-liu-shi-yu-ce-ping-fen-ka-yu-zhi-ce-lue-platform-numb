from fastapi import Request, Response
from sqlalchemy.orm import Session

from src.schemas.score import ScoreCreateRequest
from src.services import audit_service, score_service


def list_batches(db: Session, limit: int = 20) -> dict:
    return {"items": score_service.list_batches(db, limit)}


def get_batch(db: Session, batch_id: int, include_results: bool = True) -> dict:
    batch = score_service.get_batch(db, batch_id)
    return score_service.batch_payload(batch, include_results=include_results)


def create_batch(db: Session, payload: ScoreCreateRequest, actor: dict, request: Request) -> dict:
    batch = score_service.create_score_batch(
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
        action="score.create",
        resource_type="score_batch",
        resource_id=str(batch.id),
        detail={
            "batch_no": batch.batch_no,
            "threshold": batch.threshold,
            "budget_total": batch.budget_total,
            "selected_count": batch.selected_count,
        },
        ip=request.client.host if request.client else "",
        request_id=getattr(request.state, "request_id", ""),
    )
    return score_service.batch_payload(batch)


def publish(db: Session, batch_id: int, actor: dict, request: Request) -> dict:
    payload = score_service.publish_batch(db, batch_id, actor["email"])
    audit_service.record(
        db,
        actor_email=actor["email"],
        actor_role=actor["role"],
        action="score.publish",
        resource_type="score_batch",
        resource_id=str(batch_id),
        detail={"threshold": payload.get("threshold")},
        ip=request.client.host if request.client else "",
        request_id=getattr(request.state, "request_id", ""),
    )
    return payload


def export(db: Session, batch_id: int, actor: dict) -> Response:
    owner_email = actor["email"] if actor["role"] == "csm" else None
    csv_text, filename = score_service.export_csv(db, batch_id, owner_email)
    return Response(
        content=csv_text.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
