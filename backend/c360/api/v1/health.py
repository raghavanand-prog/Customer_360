from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ...db import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    """Liveness only -- no dependency checks, so a DB blip never restarts a healthy app."""
    return {"status": "ok"}


@router.get("/health/detail")
def health_detail(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    last_run = db.execute(text(
        "SELECT run_id, finished_at FROM pipeline_runs WHERE status='succeeded' ORDER BY run_id DESC LIMIT 1"
    )).mappings().first()
    counts = db.execute(text(
        "SELECT (SELECT count(*) FROM customers) AS customers, (SELECT count(*) FROM orders) AS orders"
    )).mappings().first()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "up" if db_ok else "down",
        "last_successful_run": dict(last_run) if last_run else None,
        "row_counts": dict(counts) if counts else {},
    }
