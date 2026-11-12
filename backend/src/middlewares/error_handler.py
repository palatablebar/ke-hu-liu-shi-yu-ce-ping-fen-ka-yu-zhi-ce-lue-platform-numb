"""Request id propagation, uniform JSON errors and 404 fallbacks."""
from __future__ import annotations

import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils.logger import log_event


def _error(code: str, message: str, request_id: str, status_code: int, detail=None) -> JSONResponse:
    body = {"error": {"code": code, "message": message, "request_id": request_id}}
    if detail is not None:
        body["error"]["detail"] = detail
    return JSONResponse(status_code=status_code, content=body)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def handle_http_error(request: Request, exc: HTTPException):
        request_id = getattr(request.state, "request_id", "-")
        code = {401: "unauthorized", 403: "forbidden", 404: "not_found", 409: "conflict", 429: "rate_limited"}.get(
            exc.status_code, "http_error"
        )
        message = exc.detail if isinstance(exc.detail, str) else "request failed"
        if isinstance(exc.detail, dict):
            message = exc.detail.get("message", message)
            detail = exc.detail
        else:
            detail = None
        return _error(code, message, request_id, exc.status_code, detail)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        request_id = getattr(request.state, "request_id", "-")
        return _error("validation_error", "请求参数不合法", request_id, 422, exc.errors())

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "-")
        log_event("UNHANDLED_ERROR", path=request.url.path, error=f"{type(exc).__name__}: {exc}")
        return _error("internal_error", "服务内部错误，请稍后重试", request_id, 500)
