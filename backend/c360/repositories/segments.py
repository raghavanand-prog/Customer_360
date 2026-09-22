from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def list_segments(db: Session) -> list[dict]:
    rows = db.execute(text("""
        SELECT s.segment_id, s.name, s.description, s.current_version, s.is_active,
               (SELECT count(*) FROM segment_members sm WHERE sm.segment_id = s.segment_id) AS member_count,
               (SELECT max(computed_at) FROM segment_run_stats srs WHERE srs.segment_id = s.segment_id) AS last_computed_at
        FROM segments s ORDER BY s.segment_id
    """)).mappings().all()
    return [dict(r) for r in rows]


def get_segment(db: Session, segment_id: str) -> dict | None:
    row = db.execute(text("SELECT * FROM segments WHERE segment_id = :id"), {"id": segment_id}).mappings().first()
    if not row:
        return None
    version = db.execute(
        text("SELECT * FROM segment_versions WHERE segment_id = :id AND version = :v"),
        {"id": segment_id, "v": row["current_version"]}).mappings().first()
    history = db.execute(
        text("SELECT * FROM segment_run_stats WHERE segment_id = :id ORDER BY computed_at DESC LIMIT 20"),
        {"id": segment_id}).mappings().all()
    return {"segment": dict(row), "version": dict(version) if version else None,
            "history": [dict(h) for h in history]}


def get_segment_members(db: Session, segment_id: str, limit: int, offset: int) -> list[dict]:
    rows = db.execute(text("""
        SELECT sm.canonical_customer_id, c.full_name_display, c.primary_email, sm.entered_on
        FROM segment_members sm JOIN customers c ON c.canonical_customer_id = sm.canonical_customer_id
        WHERE sm.segment_id = :id ORDER BY sm.entered_on DESC LIMIT :limit OFFSET :offset
    """), {"id": segment_id, "limit": limit, "offset": offset}).mappings().all()
    return [dict(r) for r in rows]
