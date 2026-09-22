from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...db import get_db
from ...repositories import analytics as repo
from ..deps import CurrentUser, require_role

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
def summary(db: Session = Depends(get_db), user: CurrentUser = Depends(require_role("viewer"))):
    return repo.summary(db)


@router.get("/revenue")
def revenue(months: int = Query(12, ge=1, le=60), db: Session = Depends(get_db),
            user: CurrentUser = Depends(require_role("viewer"))):
    return {"items": repo.revenue_by_month(db, months)}


@router.get("/top-customers")
def top_customers(limit: int = Query(10, ge=1, le=100), db: Session = Depends(get_db),
                   user: CurrentUser = Depends(require_role("viewer"))):
    return {"items": repo.top_customers(db, limit)}


@router.get("/churn-distribution")
def churn_distribution(db: Session = Depends(get_db), user: CurrentUser = Depends(require_role("viewer"))):
    return {"items": repo.churn_distribution(db)}


@router.get("/rfm-distribution")
def rfm_distribution(db: Session = Depends(get_db), user: CurrentUser = Depends(require_role("analyst"))):
    return {"items": repo.rfm_distribution(db)}


@router.get("/repeat-rate")
def repeat_rate(db: Session = Depends(get_db), user: CurrentUser = Depends(require_role("viewer"))):
    return repo.repeat_rate(db)
