"""SQLAlchemy 2.0 engine/session wiring plus a startup schema bootstrap."""
from __future__ import annotations

import time
from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .settings import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(max_attempts: int = 20) -> None:
    """Create tables idempotently; the DB container may still be warming up."""
    from . import models_registry  # noqa: F401  (registers every model on Base.metadata)

    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            Base.metadata.create_all(bind=engine)
            return
        except Exception as exc:  # pragma: no cover - startup resilience
            last_error = exc
            time.sleep(min(attempt * 0.5, 3.0))
    raise RuntimeError(f"database not ready after {max_attempts} attempts: {last_error}")
