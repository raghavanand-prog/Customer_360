from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def latest_run_id(db: Session) -> int | None:
    return db.execute(text("SELECT max(run_id) FROM pipeline_runs WHERE status = 'succeeded'")).scalar()


def dataset_scores(db: Session, run_id: int) -> list[dict]:
    rows = db.execute(text("SELECT * FROM data_quality_results WHERE run_id = :rid ORDER BY dataset"),
                       {"rid": run_id}).mappings().all()
    return [dict(r) for r in rows]


def dataset_detail(db: Session, run_id: int, dataset: str) -> dict | None:
    dq = db.execute(text("SELECT * FROM data_quality_results WHERE run_id = :rid AND dataset = :ds"),
                     {"rid": run_id, "ds": dataset}).mappings().first()
    if not dq:
        return None
    rules = db.execute(
        text("SELECT * FROM data_quality_rule_results WHERE dq_result_id = :id ORDER BY rule_id"),
        {"id": dq["dq_result_id"]}).mappings().all()
    return {"dataset": dict(dq), "rules": [dict(r) for r in rules]}


def score_trend(db: Session, dataset: str, limit: int = 20) -> list[dict]:
    rows = db.execute(text(
        "SELECT run_id, score_overall, ruleset_hash FROM data_quality_results "
        "WHERE dataset = :ds ORDER BY run_id DESC LIMIT :limit"),
        {"ds": dataset, "limit": limit}).mappings().all()
    return [dict(r) for r in rows]


def quarantined_records(db: Session, dataset: str | None, dq_status: str | None, limit: int, offset: int) -> list[dict]:
    clauses = ["1=1"]
    params: dict = {"limit": limit, "offset": offset}
    if dataset:
        clauses.append("dataset = :ds")
        params["ds"] = dataset
    if dq_status:
        clauses.append("dq_status = :status")
        params["status"] = dq_status
    sql = f"""SELECT quarantine_id, dataset, dq_status, failed_rules, remediation_status
              FROM quarantined_records WHERE {' AND '.join(clauses)}
              ORDER BY quarantine_id DESC LIMIT :limit OFFSET :offset"""
    return [dict(r) for r in db.execute(text(sql), params).mappings().all()]
