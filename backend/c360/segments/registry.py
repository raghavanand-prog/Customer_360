"""Field registry for the segment rule AST (§14.4).

Only fields declared here can appear in a rule; the compiler refuses
anything else at load time, before any evaluation runs.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldDef:
    name: str
    sql_expression: str
    data_type: str  # "numeric" | "string" | "boolean" | "date"
    allowed_operators: tuple[str, ...]
    nullable: bool = True


FIELD_REGISTRY: dict[str, FieldDef] = {
    "total_spend": FieldDef("total_spend", "cm.total_spend", "numeric", (">", ">=", "<", "<=", "=", "!=")),
    "order_count": FieldDef("order_count", "cm.order_count", "numeric", (">", ">=", "<", "<=", "=", "!="), nullable=False),
    "aov": FieldDef("aov", "cm.aov", "numeric", (">", ">=", "<", "<=", "=", "!=")),
    "days_since_last_order": FieldDef("days_since_last_order", "cm.days_since_last_order", "numeric",
                                       (">", ">=", "<", "<=", "=", "!=")),
    "days_since_first_seen": FieldDef("days_since_first_seen", "(current_date - c.created_at::date)", "numeric",
                                       (">", ">=", "<", "<=", "=", "!=")),
    "churn_risk_band": FieldDef("churn_risk_band", "cm.churn_risk_band", "string", ("=", "!=", "IN", "NOT IN"), nullable=False),
    "engagement_score": FieldDef("engagement_score", "cm.engagement_score", "numeric", (">", ">=", "<", "<=", "=", "!=")),
    "cart_abandon_sessions_90d": FieldDef("cart_abandon_sessions_90d", "cm.cart_abandon_sessions_90d", "numeric",
                                           (">", ">=", "<", "<=", "=", "!="), nullable=False),
    "country_code": FieldDef("country_code", "c.country_code", "string", ("=", "!=", "IN", "NOT IN")),
    "rfm_segment": FieldDef("rfm_segment", "cm.rfm_segment", "string", ("=", "!=", "IN", "NOT IN")),
}
