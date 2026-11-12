"""churnmod API entrypoint.

Middleware order (outermost first):
    CORS -> RequestId -> Auth -> RateLimit -> Audit -> routes -> error handlers
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.database import init_db
from src.config.settings import settings
from src.middlewares.audit_logger import AuditMiddleware
from src.middlewares.auth import AuthMiddleware
from src.middlewares.error_handler import RequestIdMiddleware, install_error_handlers
from src.middlewares.rate_limit import RateLimitMiddleware
from src.routes import account, audit, auth, feature, health, meta, model, score
from src.utils.logger import log_event


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.SEED_DEMO:
        try:
            from scripts.seed_demo import run_seed

            result = run_seed()
            log_event("SEED_DEMO_FINISHED", **result)
        except Exception as exc:  # seed must never block startup
            log_event("SEED_DEMO_FAILED", error=f"{type(exc).__name__}: {exc}")
    yield


app = FastAPI(
    title="Churn Chart API",
    description="客户流失预测评分卡与阈值策略台 — 安澜云服务客户成功部",
    version="1.0.0",
    lifespan=lifespan,
)

install_error_handlers(app)
app.add_middleware(AuditMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "Content-Disposition"],
)

for _prefix in ("", "/api"):
    app.include_router(health.router, prefix=_prefix)
    app.include_router(auth.router, prefix=_prefix)
    app.include_router(account.router, prefix=_prefix)
    app.include_router(feature.router, prefix=_prefix)
    app.include_router(model.router, prefix=_prefix)
    app.include_router(score.router, prefix=_prefix)
    app.include_router(audit.router, prefix=_prefix)
    app.include_router(meta.router, prefix=_prefix)


@app.get("/")
def index() -> dict:
    return {
        "service": "churnmod-backend",
        "brand": "churnmod",
        "docs": "/docs",
        "endpoints": [
            "/health",
            "/auth/login",
            "/meta/overview",
            "/accounts",
            "/accounts/{code}",
            "/features",
            "/models",
            "/models/train",
            "/models/{id}",
            "/scores",
            "/scores/{id}",
            "/scores/{id}/export",
            "/scores/{id}/publish",
        ],
    }
