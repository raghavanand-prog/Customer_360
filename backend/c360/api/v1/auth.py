from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...config import Settings, get_settings
from ...db import get_db
from ...repositories import users as users_repo
from ...security.hashing import verify_password
from ...security.jwt_tokens import create_access_token, create_refresh_token, decode_token
from ..deps import get_current_user, CurrentUser
from ..errors import ApiError

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    user = users_repo.get_user_by_email(db, body.email)
    if not user or not user["is_active"] or not verify_password(body.password, user["password_hash"]):
        raise ApiError(401, "unauthenticated", "Invalid email or password")
    roles = users_repo.get_user_roles(db, user["user_id"])
    access = create_access_token(settings, user["user_id"], user["email"], roles)
    refresh, jti, family = create_refresh_token(settings, user["user_id"])
    expires_at = decode_token(settings, refresh)["exp"]
    users_repo.store_refresh_token(db, jti, user["user_id"], hashlib.sha256(refresh.encode()).hexdigest(), family,
                                    datetime.fromtimestamp(expires_at, tz=timezone.utc))
    users_repo.touch_last_login(db, user["user_id"])
    users_repo.write_audit_log(db, user["user_id"], user["email"], roles[0] if roles else None,
                                "login", "user", str(user["user_id"]), request.state.request_id)
    return TokenResponse(access_token=access, refresh_token=refresh, expires_in=settings.access_token_ttl_minutes * 60,
                          user={"id": user["user_id"], "email": user["email"], "full_name": user["full_name"], "roles": roles})


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(body: RefreshRequest, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    try:
        payload = decode_token(settings, body.refresh_token)
    except Exception:
        raise ApiError(401, "unauthenticated", "Invalid refresh token")
    if payload.get("type") != "refresh":
        raise ApiError(401, "unauthenticated", "Wrong token type")
    stored = users_repo.get_refresh_token(db, payload["jti"])
    if not stored or stored["is_revoked"]:
        if stored:
            users_repo.revoke_family(db, stored["family_id"])
        raise ApiError(401, "token_reuse_detected", "Refresh token reuse detected; session revoked")

    user_id = int(payload["sub"])
    roles = users_repo.get_user_roles(db, user_id)
    email = payload.get("email")
    users_repo.revoke_token(db, payload["jti"])
    new_access = create_access_token(settings, user_id, email or "", roles)
    new_refresh, new_jti, family = create_refresh_token(settings, user_id, family_id=stored["family_id"])
    expires_at = decode_token(settings, new_refresh)["exp"]
    users_repo.store_refresh_token(db, new_jti, user_id, hashlib.sha256(new_refresh.encode()).hexdigest(), family,
                                    datetime.fromtimestamp(expires_at, tz=timezone.utc))
    return TokenResponse(access_token=new_access, refresh_token=new_refresh,
                          expires_in=settings.access_token_ttl_minutes * 60,
                          user={"id": user_id, "email": email, "full_name": None, "roles": roles})


@router.post("/logout", status_code=204)
def logout(body: RefreshRequest, db: Session = Depends(get_db), settings: Settings = Depends(get_settings),
           user: CurrentUser = Depends(get_current_user)):
    try:
        payload = decode_token(settings, body.refresh_token)
        users_repo.revoke_token(db, payload["jti"])
    except Exception:
        pass
    return None


@router.get("/me")
def me(user: CurrentUser = Depends(get_current_user)):
    return {"id": user.user_id, "email": user.email, "roles": user.roles}
