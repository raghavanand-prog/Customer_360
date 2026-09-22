from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt

from ..config import Settings


def create_access_token(settings: Settings, user_id: int, email: str, roles: list[str]) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id), "email": email, "roles": roles, "type": "access",
        "iat": now, "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(settings: Settings, user_id: int, family_id: str | None = None) -> tuple[str, str, str]:
    jti = str(uuid.uuid4())
    family_id = family_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=settings.refresh_token_ttl_days)
    payload = {"sub": str(user_id), "jti": jti, "family": family_id, "type": "refresh",
               "iat": now, "exp": expires_at}
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, jti, family_id


def decode_token(settings: Settings, token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
