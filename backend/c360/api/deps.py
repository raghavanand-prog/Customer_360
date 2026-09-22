from __future__ import annotations

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..security.jwt_tokens import decode_token
from ..security.rbac import has_at_least
from .errors import ApiError

bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser:
    def __init__(self, user_id: int, email: str, roles: list[str]):
        self.user_id = user_id
        self.email = email
        self.roles = roles


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    if credentials is None:
        raise ApiError(401, "unauthenticated", "Missing bearer token")
    try:
        payload = decode_token(settings, credentials.credentials)
    except Exception:
        raise ApiError(401, "token_expired", "Invalid or expired token")
    if payload.get("type") != "access":
        raise ApiError(401, "unauthenticated", "Wrong token type")
    return CurrentUser(user_id=int(payload["sub"]), email=payload["email"], roles=payload.get("roles", []))


def require_role(minimum: str):
    def _checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not has_at_least(user.roles, minimum):
            raise ApiError(403, "insufficient_role", f"Requires role >= {minimum}")
        return user
    return _checker


class Pagination:
    def __init__(self, limit: int = Query(25, ge=1, le=100), cursor: str | None = Query(None)):
        self.limit = limit
        self.cursor = cursor


def db_session(session: Session = Depends(get_db)) -> Session:
    return session
