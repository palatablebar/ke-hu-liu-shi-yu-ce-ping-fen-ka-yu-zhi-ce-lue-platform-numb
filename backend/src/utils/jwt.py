from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from src.config.settings import settings


def create_access_token(subject: str, role: str, extra: dict[str, Any] | None = None) -> str:
    issued = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": issued,
        "exp": issued + timedelta(hours=settings.JWT_EXPIRE_HOURS),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
