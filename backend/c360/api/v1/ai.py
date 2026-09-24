from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ...ai.agent import run_agent
from ...config import Settings, get_settings
from ...db import get_db
from ...repositories import ai as ai_repo
from ...security.rbac import highest_role
from ..deps import CurrentUser, require_role
from ..errors import ApiError
from .customers import _resolve_customer

router = APIRouter(prefix="/ai", tags=["ai"])


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    customer_id: str | None = Field(None, max_length=100)


class SourceRefOut(BaseModel):
    source: str
    section: str
    score: float


class AskResponse(BaseModel):
    answer: str
    tools_called: list[str]
    tool_denied: list[str]
    sources: list[SourceRefOut]
    provider: str
    model: str | None
    configured: bool


@router.post("/ask", response_model=AskResponse)
def ask(
    body: AskRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("viewer")),
    settings: Settings = Depends(get_settings),
):
    resolved_customer_id: str | None = None
    if body.customer_id:
        try:
            resolved_customer_id = _resolve_customer(db, body.customer_id)
        except ApiError:
            # An unresolvable customer id is not an assistant-request
            # failure -- fall through and let the agent answer with
            # whatever documentation context it can, explicitly noting no
            # customer data was found. Never raise a raw SQL/lookup error
            # into an AI response.
            resolved_customer_id = None

    role = highest_role(user.roles)
    result = run_agent(db, role, settings, body.question, resolved_customer_id)

    ai_repo.write_ai_audit(
        db, user_id=user.user_id, actor_email=user.email, customer_id=resolved_customer_id,
        question=body.question, tools_called=result.tools_called,
        sources=[{"source": s.source, "section": s.section, "score": s.score} for s in result.sources],
        provider=result.provider, model=result.model, configured=result.configured,
        request_id=getattr(request.state, "request_id", None),
    )

    return AskResponse(
        answer=result.answer,
        tools_called=result.tools_called,
        tool_denied=result.tool_denied,
        sources=[SourceRefOut(source=s.source, section=s.section, score=s.score) for s in result.sources],
        provider=result.provider,
        model=result.model,
        configured=result.configured,
    )


@router.get("/status")
def status(db: Session = Depends(get_db), settings: Settings = Depends(get_settings),
           user: CurrentUser = Depends(require_role("viewer"))):
    return {
        "configured": bool(settings.anthropic_api_key),
        "provider": "anthropic" if settings.anthropic_api_key else "none",
        "knowledge_chunks": ai_repo.count_chunks(db),
    }
