"""SQL analytics catalogue (§13). Every query is bounded and parameterised."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def summary(db: Session) -> dict:
    row = db.execute(text("""
        SELECT
            (SELECT count(*) FROM customers) AS total_customers,
            (SELECT count(*) FROM customer_metrics WHERE churn_risk_band = 'active') AS active_customers,
            (SELECT count(*) FROM customer_metrics WHERE churn_risk_band = 'at_risk') AS at_risk_customers,
            (SELECT coalesce(sum(revenue_amount), 0) FROM orders) AS total_revenue,
            (SELECT count(*) FROM orders WHERE order_type = 'sale') AS total_orders,
            (SELECT coalesce(avg(aov), 0) FROM customer_metrics) AS avg_aov,
            (SELECT coalesce(avg(score_overall), 0) FROM data_quality_results
                WHERE run_id = (SELECT max(run_id) FROM pipeline_runs WHERE status = 'succeeded')) AS dq_score,
            (SELECT max(run_id) FROM pipeline_runs WHERE status = 'succeeded') AS last_run_id
    """)).mappings().first()
    return dict(row)


def revenue_by_month(db: Session, months: int = 12) -> list[dict]:
    rows = db.execute(text("""
        SELECT date_trunc('month', order_ts)::date AS period, sum(revenue_amount) AS revenue, count(*) AS orders
        FROM orders WHERE order_ts >= now() - (:months || ' months')::interval
        GROUP BY 1 ORDER BY 1
    """), {"months": months}).mappings().all()
    return [dict(r) for r in rows]


def top_customers(db: Session, limit: int = 10) -> list[dict]:
    rows = db.execute(text("""
        SELECT c.canonical_customer_id, c.full_name_display, cm.total_spend, cm.order_count
        FROM customer_metrics cm JOIN customers c ON c.canonical_customer_id = cm.canonical_customer_id
        ORDER BY cm.total_spend DESC NULLS LAST LIMIT :limit
    """), {"limit": limit}).mappings().all()
    return [dict(r) for r in rows]


def churn_distribution(db: Session) -> list[dict]:
    rows = db.execute(text(
        "SELECT churn_risk_band, count(*) AS customers FROM customer_metrics GROUP BY 1 ORDER BY 1"
    )).mappings().all()
    return [dict(r) for r in rows]


def rfm_distribution(db: Session) -> list[dict]:
    rows = db.execute(text(
        "SELECT rfm_segment, count(*) AS customers FROM customer_metrics "
        "WHERE rfm_segment IS NOT NULL GROUP BY 1 ORDER BY 1"
    )).mappings().all()
    return [dict(r) for r in rows]


def repeat_rate(db: Session) -> dict:
    row = db.execute(text("""
        SELECT
            count(*) FILTER (WHERE order_count >= 2)::float / NULLIF(count(*) FILTER (WHERE order_count >= 1), 0) AS repeat_rate,
            count(*) FILTER (WHERE order_count >= 1) AS purchasers
        FROM customer_metrics
    """)).mappings().first()
    return dict(row)
