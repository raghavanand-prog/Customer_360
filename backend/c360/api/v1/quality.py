from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...db import get_db
from ...repositories import quality as repo
from ..deps import CurrentUser, require_role
from ..errors import ApiError

router = APIRouter(prefix="/quality", tags=["quality"])


@router.get("/summary")
def summary(db: Session = Depends(get_db), user: CurrentUser = Depends(require_role("viewer"))):
    run_id = repo.latest_run_id(db)
    if run_id is None:
        return {"run_id": None, "datasets": []}
    return {"run_id": run_id, "datasets": repo.dataset_scores(db, run_id)}


@router.get("/datasets")
def datasets(db: Session = Depends(get_db), user: CurrentUser = Depends(require_role("viewer"))):
    run_id = repo.latest_run_id(db)
    if run_id is None:
        return {"items": []}
    return {"items": repo.dataset_scores(db, run_id)}


@router.get("/datasets/{dataset}")
def dataset_detail(dataset: str, db: Session = Depends(get_db), user: CurrentUser = Depends(require_role("viewer"))):
    run_id = repo.latest_run_id(db)
    if run_id is None:
        raise ApiError(404, "not_found", "No pipeline run available")
    detail = repo.dataset_detail(db, run_id, dataset)
    if not detail:
        raise ApiError(404, "not_found", "No quality result for this dataset")
    return detail


@router.get("/datasets/{dataset}/trend")
def dataset_trend(dataset: str, db: Session = Depends(get_db), user: CurrentUser = Depends(require_role("viewer"))):
    return {"items": repo.score_trend(db, dataset)}


@router.get("/records")
def records(dataset: str | None = Query(None), dq_status: str | None = Query(None),
            limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0),
            db: Session = Depends(get_db), user: CurrentUser = Depends(require_role("analyst"))):
    return {"items": repo.quarantined_records(db, dataset, dq_status, limit, offset)}
