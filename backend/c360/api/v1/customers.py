from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...config import Settings, get_settings
from ...db import get_db
from ...repositories import customers as repo
from ...security.masking import apply_profile_masking
from ...security.rbac import highest_role
from ..deps import CurrentUser, require_role
from ..errors import ApiError

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("")
def search_customers(
    q: str | None = Query(None),
    churn_risk_band: str | None = Query(None),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("viewer")),
    settings: Settings = Depends(get_settings),
):
    rows = repo.search_customers(db, q, churn_risk_band, limit, offset)
    role = highest_role(user.roles)
    rows = [apply_profile_masking(r, role, settings.mask_pii_roles_set) for r in rows]
    return {"items": rows, "limit": limit, "offset": offset}


def _resolve_customer(db: Session, canonical_id: str) -> str:
    customer = repo.get_customer(db, canonical_id)
    if customer:
        return canonical_id
    crosswalk = repo.resolve_crosswalk(db, canonical_id)
    if crosswalk and crosswalk["status"] == "merged":
        return crosswalk["canonical_customer_id"]
    if crosswalk and crosswalk["status"] == "split":
        raise ApiError(409, "identity_ambiguous", "This canonical ID was split into multiple successors",
                        {"successors": []})
    raise ApiError(404, "not_found", "Customer not found")


@router.get("/{canonical_id}")
def get_customer(canonical_id: str, db: Session = Depends(get_db),
                  user: CurrentUser = Depends(require_role("viewer")), settings: Settings = Depends(get_settings)):
    resolved_id = _resolve_customer(db, canonical_id)
    customer = repo.get_customer(db, resolved_id)
    role = highest_role(user.roles)
    return apply_profile_masking(customer, role, settings.mask_pii_roles_set)


@router.get("/{canonical_id}/profile")
def get_profile(canonical_id: str, db: Session = Depends(get_db),
                 user: CurrentUser = Depends(require_role("viewer")), settings: Settings = Depends(get_settings)):
    resolved_id = _resolve_customer(db, canonical_id)
    customer = repo.get_customer(db, resolved_id)
    role = highest_role(user.roles)
    profile = {
        "identity": {
            "canonical_customer_id": resolved_id,
            "identities": repo.get_customer_identities(db, resolved_id),
        },
        "profile": apply_profile_masking(customer, role, settings.mask_pii_roles_set),
        "metrics": repo.get_customer_metrics(db, resolved_id),
        "orders": repo.get_customer_orders(db, resolved_id, 10),
        "segments": repo.get_customer_segments(db, resolved_id),
        "quality": repo.get_quarantined_for_customer(db, resolved_id),
    }
    return profile


@router.get("/{canonical_id}/metrics")
def get_metrics(canonical_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(require_role("viewer"))):
    resolved_id = _resolve_customer(db, canonical_id)
    metrics = repo.get_customer_metrics(db, resolved_id)
    if not metrics:
        raise ApiError(404, "not_found", "No metrics for this customer")
    return metrics


@router.get("/{canonical_id}/identities")
def get_identities(canonical_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(require_role("analyst"))):
    resolved_id = _resolve_customer(db, canonical_id)
    return {"items": repo.get_customer_identities(db, resolved_id)}


@router.get("/{canonical_id}/orders")
def get_orders(canonical_id: str, limit: int = Query(25, ge=1, le=100), db: Session = Depends(get_db),
                user: CurrentUser = Depends(require_role("viewer"))):
    resolved_id = _resolve_customer(db, canonical_id)
    return {"items": repo.get_customer_orders(db, resolved_id, limit)}


@router.get("/{canonical_id}/timeline")
def get_timeline(canonical_id: str, limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db),
                  user: CurrentUser = Depends(require_role("viewer"))):
    resolved_id = _resolve_customer(db, canonical_id)
    return {"items": repo.get_customer_timeline(db, resolved_id, limit)}


@router.get("/{canonical_id}/segments")
def get_segments(canonical_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(require_role("viewer"))):
    resolved_id = _resolve_customer(db, canonical_id)
    return {"items": repo.get_customer_segments(db, resolved_id)}


@router.get("/{canonical_id}/quality")
def get_quality(canonical_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(require_role("analyst"))):
    resolved_id = _resolve_customer(db, canonical_id)
    return {"items": repo.get_quarantined_for_customer(db, resolved_id)}
