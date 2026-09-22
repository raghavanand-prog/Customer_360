from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_user_by_email(db: Session, email: str) -> dict | None:
    row = db.execute(text("SELECT user_id, email, password_hash, full_name, is_active FROM users WHERE email = :email"),
                      {"email": email}).mappings().first()
    return dict(row) if row else None


def get_user_roles(db: Session, user_id: int) -> list[str]:
    rows = db.execute(text("SELECT role_name FROM user_roles WHERE user_id = :uid"), {"uid": user_id}).scalars().all()
    return list(rows)


def create_user(db: Session, email: str, password_hash: str, full_name: str, roles: list[str]) -> int:
    row = db.execute(
        text("INSERT INTO users (email, password_hash, full_name) VALUES (:email, :ph, :fn) RETURNING user_id"),
        {"email": email, "ph": password_hash, "fn": full_name}).first()
    user_id = row[0]
    for role in roles:
        db.execute(text("INSERT INTO user_roles (user_id, role_name) VALUES (:uid, :role)"),
                   {"uid": user_id, "role": role})
    db.commit()
    return user_id


def touch_last_login(db: Session, user_id: int) -> None:
    db.execute(text("UPDATE users SET last_login_at = now() WHERE user_id = :uid"), {"uid": user_id})
    db.commit()


def store_refresh_token(db: Session, jti: str, user_id: int, token_hash: str, family_id: str, expires_at) -> None:
    db.execute(
        text("INSERT INTO refresh_tokens (jti, user_id, token_hash, family_id, expires_at) "
             "VALUES (:jti, :uid, :th, :fam, :exp)"),
        {"jti": jti, "uid": user_id, "th": token_hash, "fam": family_id, "exp": expires_at})
    db.commit()


def get_refresh_token(db: Session, jti: str) -> dict | None:
    row = db.execute(text("SELECT * FROM refresh_tokens WHERE jti = :jti"), {"jti": jti}).mappings().first()
    return dict(row) if row else None


def revoke_family(db: Session, family_id: str) -> None:
    db.execute(text("UPDATE refresh_tokens SET is_revoked = TRUE WHERE family_id = :fam"), {"fam": family_id})
    db.commit()


def revoke_token(db: Session, jti: str) -> None:
    db.execute(text("UPDATE refresh_tokens SET is_revoked = TRUE WHERE jti = :jti"), {"jti": jti})
    db.commit()


def write_audit_log(db: Session, user_id: int | None, actor_email: str | None, actor_role: str | None,
                     action: str, resource_type: str | None, resource_id: str | None,
                     request_id: str | None, outcome: str = "success") -> None:
    db.execute(
        text("INSERT INTO audit_logs (user_id, actor_email, actor_role, action, resource_type, resource_id, "
             "outcome, request_id) VALUES (:uid, :email, :role, :action, :rtype, :rid, :outcome, :reqid)"),
        {"uid": user_id, "email": actor_email, "role": actor_role, "action": action,
         "rtype": resource_type, "rid": resource_id, "outcome": outcome, "reqid": request_id})
    db.commit()
