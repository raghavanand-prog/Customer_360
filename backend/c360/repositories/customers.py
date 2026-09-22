from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def search_customers(db: Session, q: str | None, churn_risk_band: str | None,
                      limit: int, offset: int) -> list[dict]:
    clauses = ["1=1"]
    params: dict = {"limit": limit, "offset": offset}
    if q:
        clauses.append("(c.full_name_display ILIKE :q OR c.primary_email ILIKE :q OR c.primary_phone ILIKE :q "
                        "OR c.canonical_customer_id = :q_exact)")
        params["q"] = f"%{q}%"
        params["q_exact"] = q
    if churn_risk_band:
        clauses.append("cm.churn_risk_band = :band")
        params["band"] = churn_risk_band
    sql = f"""
        SELECT c.canonical_customer_id, c.first_name, c.last_name, c.full_name_display,
               c.primary_email, c.primary_phone, c.country_code, c.account_status,
               cm.total_spend, cm.order_count, cm.churn_risk_band, cm.last_order_at
        FROM customers c
        LEFT JOIN customer_metrics cm ON cm.canonical_customer_id = c.canonical_customer_id
        WHERE {' AND '.join(clauses)}
        ORDER BY cm.total_spend DESC NULLS LAST, c.canonical_customer_id
        LIMIT :limit OFFSET :offset
    """
    return [dict(r) for r in db.execute(text(sql), params).mappings().all()]


def get_customer(db: Session, canonical_id: str) -> dict | None:
    row = db.execute(text("SELECT * FROM customers WHERE canonical_customer_id = :id"),
                      {"id": canonical_id}).mappings().first()
    return dict(row) if row else None


def resolve_crosswalk(db: Session, canonical_id: str) -> dict | None:
    row = db.execute(
        text("SELECT * FROM identity_crosswalk WHERE prior_canonical_customer_id = :id"),
        {"id": canonical_id}).mappings().first()
    return dict(row) if row else None


def get_customer_metrics(db: Session, canonical_id: str) -> dict | None:
    row = db.execute(text("SELECT * FROM customer_metrics WHERE canonical_customer_id = :id"),
                      {"id": canonical_id}).mappings().first()
    return dict(row) if row else None


def get_customer_identities(db: Session, canonical_id: str) -> list[dict]:
    rows = db.execute(
        text("SELECT * FROM customer_identities WHERE canonical_customer_id = :id ORDER BY source_system"),
        {"id": canonical_id}).mappings().all()
    return [dict(r) for r in rows]


def get_customer_orders(db: Session, canonical_id: str, limit: int) -> list[dict]:
    rows = db.execute(
        text("SELECT order_id, order_ts, order_status, order_type, currency, net_amount, revenue_amount, "
             "channel, payment_method FROM orders WHERE canonical_customer_id = :id "
             "ORDER BY order_ts DESC LIMIT :limit"),
        {"id": canonical_id, "limit": limit}).mappings().all()
    return [dict(r) for r in rows]


def get_customer_segments(db: Session, canonical_id: str) -> list[dict]:
    rows = db.execute(
        text("SELECT sm.segment_id, s.name, sm.entered_on FROM segment_members sm "
             "JOIN segments s ON s.segment_id = sm.segment_id WHERE sm.canonical_customer_id = :id"),
        {"id": canonical_id}).mappings().all()
    return [dict(r) for r in rows]


def get_customer_timeline(db: Session, canonical_id: str, limit: int) -> list[dict]:
    sql = """
        SELECT event_ts, event_kind, summary FROM (
            SELECT order_ts AS event_ts, 'order' AS event_kind,
                   'Order ' || order_id || ' - ' || order_status AS summary
            FROM orders WHERE canonical_customer_id = :id
            UNION ALL
            SELECT event_ts, 'web_event', event_type FROM web_events WHERE canonical_customer_id = :id
            UNION ALL
            SELECT created_at, 'support_ticket', subject FROM support_tickets WHERE canonical_customer_id = :id
            UNION ALL
            SELECT event_ts, 'marketing', campaign_name FROM marketing_events WHERE canonical_customer_id = :id
        ) unioned
        ORDER BY event_ts DESC LIMIT :limit
    """
    rows = db.execute(text(sql), {"id": canonical_id, "limit": limit}).mappings().all()
    return [dict(r) for r in rows]


def get_quarantined_for_customer(db: Session, canonical_id: str) -> list[dict]:
    rows = db.execute(
        text("SELECT quarantine_id, dataset, dq_status, failed_rules FROM quarantined_records "
             "WHERE canonical_customer_id = :id ORDER BY quarantine_id DESC LIMIT 50"),
        {"id": canonical_id}).mappings().all()
    return [dict(r) for r in rows]
