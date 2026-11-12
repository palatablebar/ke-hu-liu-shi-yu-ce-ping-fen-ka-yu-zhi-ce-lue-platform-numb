from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from src.constants.messages import MSG_LOGIN_FAILED
from src.schemas.auth import LoginRequest
from src.services import audit_service, auth_service


def login(db: Session, payload: LoginRequest, request: Request) -> dict:
    user = auth_service.authenticate(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail=MSG_LOGIN_FAILED)
    token = auth_service.issue_token(user)
    audit_service.record(
        db,
        actor_email=user.email,
        actor_role=user.role,
        action="auth.login",
        resource_type="user",
        resource_id=str(user.id),
        detail={"email": user.email, "role": user.role},
        ip=request.client.host if request.client else "",
        request_id=getattr(request.state, "request_id", ""),
    )
    return {"access_token": token, "token_type": "bearer", "user": auth_service.public_user(user)}


def me(db: Session, request: Request) -> dict:
    user = auth_service.get_user_by_email(db, getattr(request.state, "user_email", ""))
    if user is None:
        raise HTTPException(status_code=401, detail=MSG_LOGIN_FAILED)
    return auth_service.public_user(user)
