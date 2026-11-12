"""JWT authentication middleware: attaches the caller identity to request.state."""
from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.constants.messages import MSG_TOKEN_INVALID, MSG_TOKEN_MISSING
from src.utils.jwt import decode_token

PUBLIC_PATHS = {
    "/health",
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/healthz",
    "/auth/login",
}


def normalized_path(path: str) -> str:
    return path[4:] if path.startswith("/api/") else path


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = normalized_path(request.url.path)
        request.state.user_email = ""
        request.state.user_role = ""
        request.state.claims = None
        if path in PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)

        header = request.headers.get("Authorization", "")
        token = header[7:].strip() if header.lower().startswith("bearer ") else ""
        if not token:
            return JSONResponse(
                status_code=401,
                content={"error": {"code": "unauthorized", "message": MSG_TOKEN_MISSING,
                                   "request_id": getattr(request.state, "request_id", "-")}},
            )
        try:
            claims = decode_token(token)
        except Exception:
            return JSONResponse(
                status_code=401,
                content={"error": {"code": "unauthorized", "message": MSG_TOKEN_INVALID,
                                   "request_id": getattr(request.state, "request_id", "-")}},
            )
        request.state.claims = claims
        request.state.user_email = claims.get("sub", "")
        request.state.user_role = claims.get("role", "")
        return await call_next(request)
