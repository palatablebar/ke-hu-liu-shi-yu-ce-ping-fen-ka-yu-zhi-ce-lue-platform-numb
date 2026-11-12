"""Role based access control dependencies (real 403s, not UI hiding)."""
from __future__ import annotations

from fastapi import HTTPException, Request

from src.constants.messages import MSG_FORBIDDEN
from src.constants.roles import Role


def require_roles(*roles: Role):
    allowed = {role.value if hasattr(role, "value") else str(role) for role in roles}

    def dependency(request: Request) -> dict:
        role = getattr(request.state, "user_role", "")
        if role not in allowed:
            raise HTTPException(status_code=403, detail=MSG_FORBIDDEN)
        return {
            "email": getattr(request.state, "user_email", ""),
            "role": role,
        }

    return dependency
