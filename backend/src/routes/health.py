from fastapi import APIRouter
from sqlalchemy import text

from src.config.database import engine
from src.config.settings import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    checks = {"db": False, "redis": False}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["db"] = True
    except Exception:
        checks["db"] = False
    try:
        import redis

        client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        checks["redis"] = bool(client.ping())
    except Exception:
        checks["redis"] = False
    return {
        "status": "ok" if all(checks.values()) else "degraded",
        "service": "churnmod-backend",
        "checks": checks,
        "version": "1.0.0",
    }
