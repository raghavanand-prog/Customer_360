"""Controlled Customer360 tools for the assistant (§12 of the Adobe-JD AI phase).

Every tool wraps an *existing* repository function -- no new SQL, no new
capability the direct REST API doesn't already expose. Each tool enforces
the exact same RBAC minimum role as its equivalent `/api/v1/customers/...`
or `/api/v1/quality/...` endpoint, and applies the same PII masking. The
LLM never gets raw SQL access and never sees a tool it isn't in
`ALLOWED_TOOLS`.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..api.v1.customers import _resolve_customer
from ..repositories import customers as customers_repo
from ..repositories import quality as quality_repo
from ..repositories import segments as segments_repo
from ..security.masking import apply_profile_masking
from ..security.rbac import has_at_least


@dataclass
class ToolResult:
    name: str
    authorized: bool
    data: dict | list | None
    error: str | None = None


class ToolContext:
    """Bundles the request-scoped dependencies every tool needs."""

    def __init__(self, db: Session, role: str, mask_pii_roles: set[str]):
        self.db = db
        self.role = role
        self.mask_pii_roles = mask_pii_roles


def _require_role(ctx: ToolContext, minimum: str) -> bool:
    return has_at_least([ctx.role], minimum)


def get_customer_profile(ctx: ToolContext, customer_id: str) -> ToolResult:
    resolved = _resolve_customer(ctx.db, customer_id)
    customer = customers_repo.get_customer(ctx.db, resolved)
    if not customer:
        return ToolResult("get_customer_profile", True, None, error="customer not found")
    masked = apply_profile_masking(customer, ctx.role, ctx.mask_pii_roles)
    return ToolResult("get_customer_profile", True, masked)


def get_customer_metrics(ctx: ToolContext, customer_id: str) -> ToolResult:
    resolved = _resolve_customer(ctx.db, customer_id)
    metrics = customers_repo.get_customer_metrics(ctx.db, resolved)
    return ToolResult("get_customer_metrics", True, metrics)


def get_customer_segments(ctx: ToolContext, customer_id: str) -> ToolResult:
    resolved = _resolve_customer(ctx.db, customer_id)
    return ToolResult("get_customer_segments", True, customers_repo.get_customer_segments(ctx.db, resolved))


def get_customer_timeline(ctx: ToolContext, customer_id: str, limit: int = 20) -> ToolResult:
    resolved = _resolve_customer(ctx.db, customer_id)
    return ToolResult("get_customer_timeline", True, customers_repo.get_customer_timeline(ctx.db, resolved, limit))


def get_customer_identities(ctx: ToolContext, customer_id: str) -> ToolResult:
    if not _require_role(ctx, "analyst"):
        return ToolResult("get_customer_identities", False, None, error="requires analyst role or higher")
    resolved = _resolve_customer(ctx.db, customer_id)
    return ToolResult("get_customer_identities", True, customers_repo.get_customer_identities(ctx.db, resolved))


def get_customer_quality(ctx: ToolContext, customer_id: str) -> ToolResult:
    if not _require_role(ctx, "analyst"):
        return ToolResult("get_customer_quality", False, None, error="requires analyst role or higher")
    resolved = _resolve_customer(ctx.db, customer_id)
    return ToolResult("get_customer_quality", True, customers_repo.get_quarantined_for_customer(ctx.db, resolved))


def get_segment_definition(ctx: ToolContext, segment_id: str) -> ToolResult:
    segment = segments_repo.get_segment(ctx.db, segment_id)
    if not segment:
        return ToolResult("get_segment_definition", True, None, error="segment not found")
    return ToolResult("get_segment_definition", True, segment)


def get_data_quality_summary(ctx: ToolContext) -> ToolResult:
    run_id = quality_repo.latest_run_id(ctx.db)
    if run_id is None:
        return ToolResult("get_data_quality_summary", True, {"run_id": None, "datasets": []})
    return ToolResult("get_data_quality_summary", True, {"run_id": run_id, "datasets": quality_repo.dataset_scores(ctx.db, run_id)})


# The allowlist the agent is permitted to call. Anything not in this dict
# cannot be invoked, no matter what a model (real or otherwise) asks for.
TOOL_REGISTRY = {
    "get_customer_profile": get_customer_profile,
    "get_customer_metrics": get_customer_metrics,
    "get_customer_segments": get_customer_segments,
    "get_customer_timeline": get_customer_timeline,
    "get_customer_identities": get_customer_identities,
    "get_customer_quality": get_customer_quality,
    "get_segment_definition": get_segment_definition,
    "get_data_quality_summary": get_data_quality_summary,
}

CUSTOMER_SCOPED_TOOLS = {
    "get_customer_profile", "get_customer_metrics", "get_customer_segments",
    "get_customer_timeline", "get_customer_identities", "get_customer_quality",
}
