"""In-process sliding-window rate limit (per caller identity / IP)."""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.config.settings import settings
from src.constants.messages import MSG_RATE_LIMITED

WINDOW = settings.RATE_WINDOW_SECONDS
MAX_REQUESTS = settings.RATE_WINDOW_MAX
_buckets: dict[str, deque[float]] = defaultdict(deque)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.rstrip("/") in ("/health", "/healthz"):
            return await call_next(request)
        key = getattr(request.state, "user_email", "") or (request.client.host if request.client else "anon")
        now = time.monotonic()
        bucket = _buckets[key]
        while bucket and now - bucket[0] > WINDOW:
            bucket.popleft()
        if len(bucket) >= MAX_REQUESTS:
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "rate_limited", "message": MSG_RATE_LIMITED,
                                   "request_id": getattr(request.state, "request_id", "-")}},
            )
        bucket.append(now)
        return await call_next(request)
