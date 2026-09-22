from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...db import get_db
from ...repositories import pipeline as repo
from ..deps import CurrentUser, require_role
from ..errors import ApiError

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.get("/runs")
def list_runs(limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0),
              db: Session = Depends(get_db), user: CurrentUser = Depends(require_role("viewer"))):
    return {"items": repo.list_runs(db, limit, offset)}


@router.get("/runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(require_role("viewer"))):
    run = repo.get_run(db, run_id)
    if not run:
        raise ApiError(404, "not_found", "Run not found")
    return run


@router.get("/runs/{run_id}/stages")
def get_run_stages(run_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(require_role("viewer"))):
    return {"items": repo.get_run_stages(db, run_id)}


@router.get("/latest")
def latest_run(db: Session = Depends(get_db), user: CurrentUser = Depends(require_role("viewer"))):
    run = repo.latest_run(db)
    if not run:
        raise ApiError(404, "not_found", "No successful run yet")
    return run
