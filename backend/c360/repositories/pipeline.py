from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def list_runs(db: Session, limit: int, offset: int) -> list[dict]:
    rows = db.execute(text(
        "SELECT run_id, dataset_size, status, triggered_by, started_at, finished_at, duration_ms "
        "FROM pipeline_runs ORDER BY run_id DESC LIMIT :limit OFFSET :offset"),
        {"limit": limit, "offset": offset}).mappings().all()
    return [dict(r) for r in rows]


def get_run(db: Session, run_id: int) -> dict | None:
    row = db.execute(text("SELECT * FROM pipeline_runs WHERE run_id = :id"), {"id": run_id}).mappings().first()
    return dict(row) if row else None


def get_run_stages(db: Session, run_id: int) -> list[dict]:
    rows = db.execute(text(
        "SELECT * FROM pipeline_stage_runs WHERE run_id = :id ORDER BY stage_order"),
        {"id": run_id}).mappings().all()
    return [dict(r) for r in rows]


def latest_run(db: Session) -> dict | None:
    row = db.execute(text(
        "SELECT * FROM pipeline_runs WHERE status = 'succeeded' ORDER BY run_id DESC LIMIT 1")).mappings().first()
    return dict(row) if row else None
