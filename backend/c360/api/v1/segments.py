from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...db import get_db
from ...repositories import segments as repo
from ..deps import CurrentUser, require_role
from ..errors import ApiError

router = APIRouter(prefix="/segments", tags=["segments"])


@router.get("")
def list_segments(db: Session = Depends(get_db), user: CurrentUser = Depends(require_role("viewer"))):
    return {"items": repo.list_segments(db)}


@router.get("/{segment_id}")
def get_segment(segment_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(require_role("viewer"))):
    result = repo.get_segment(db, segment_id)
    if not result:
        raise ApiError(404, "not_found", "Segment not found")
    return result


@router.get("/{segment_id}/members")
def get_members(segment_id: str, limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0),
                 db: Session = Depends(get_db), user: CurrentUser = Depends(require_role("viewer"))):
    return {"items": repo.get_segment_members(db, segment_id, limit, offset)}
