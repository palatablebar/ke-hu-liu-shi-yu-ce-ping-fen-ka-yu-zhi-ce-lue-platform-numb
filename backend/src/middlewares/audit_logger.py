"""Audit middleware: records every mutating HTTP request (login, build, resolve, rule edit)."""
from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from src.config.database import SessionLocal
from src.services import audit_service
from src.utils.logger import log_event

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.method not in MUTATING_METHODS:
            return response
        path = request.url.path
        if path.startswith("/api/"):
            path = path[4:]
        try:
            db = SessionLocal()
            try:
                audit_service.record(
                    db,
                    actor_email=getattr(request.state, "user_email", ""),
                    actor_role=getattr(request.state, "user_role", ""),
                    action=f"http.{request.method.lower()}",
                    resource_type=path.strip("/").split("/")[0] or "root",
                    resource_id=",".join(path.strip("/").split("/")[1:]),
                    detail={"status_code": response.status_code, "path": path},
                    ip=request.client.host if request.client else "",
                    request_id=getattr(request.state, "request_id", ""),
                )
            finally:
                db.close()
        except Exception as exc:  # audit must never break the request
            log_event("AUDIT_WRITE_FAILED", error=str(exc))
        return response
