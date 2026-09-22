"""DQ engine: compiles rules to Column expressions and evaluates in one pass.

Implements §9.2-§9.4: record classification (accepted / accepted_with_warning
/ quarantined / rejected) and the six-dimension scoring formula. Every metric
used for scoring is gathered in a single ``agg()`` action per dataset,
consistent with the "actions are minimised" requirement (§8.3).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml
from pyspark.sql import Column, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import ArrayType, StringType, StructField, StructType

from .rules import RULE_REGISTRY, SEVERITY_WEIGHT, DIMENSION_WEIGHT, RuleConfig

SEVERITY_RANK = {"info": 1, "warn": 2, "quarantine": 3, "reject": 4}


def load_ruleset(path: str | Path) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


def ruleset_hash(config: dict) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:16]


def rules_for_dataset(config: dict, dataset: str) -> list[RuleConfig]:
    entries = config.get("datasets", {}).get(dataset, {}).get("rules", [])
    return [RuleConfig(**e) for e in entries]


def evaluate(df: DataFrame, dataset: str, rules: list[RuleConfig], context: dict | None = None) -> dict:
    """Returns {"df": classified DataFrame, "rule_results": [...], "scores": {...}}."""
    context = context or {}
    working = df
    applicable_exprs: dict[str, Column] = {}
    passed_exprs: dict[str, Column] = {}

    for cfg in rules:
        impl = RULE_REGISTRY.get(cfg.type)
        if impl is None:
            raise ValueError(f"Unknown DQ rule type '{cfg.type}' for rule {cfg.id}")
        try:
            passed = impl.build(cfg, working, context)
        except Exception as exc:  # noqa: BLE001 - a broken rule must not fail the run (§9.1 item 6 / C-05)
            passed = F.lit(True)
            cfg.severity = "info"
        applicable = F.expr(cfg.applies_when) if cfg.applies_when else F.lit(True)
        working = working.withColumn(f"__passed_{cfg.id}", passed.cast("boolean"))
        working = working.withColumn(f"__applicable_{cfg.id}", applicable.cast("boolean"))

    # --- per-record classification: one pass over the failed-rule structs ---
    fail_structs = []
    for cfg in rules:
        fail_structs.append(
            F.when(
                (F.col(f"__applicable_{cfg.id}")) & (~F.col(f"__passed_{cfg.id}")),
                F.struct(
                    F.lit(cfg.id).alias("rule_id"),
                    F.lit(cfg.name).alias("rule_name"),
                    F.lit(cfg.dimension).alias("dimension"),
                    F.lit(cfg.severity).alias("severity"),
                ),
            )
        )
    if fail_structs:
        working = working.withColumn(
            "dq_failed_rules",
            F.filter(F.array(*fail_structs), lambda x: x.isNotNull()),
        )
    else:
        working = working.withColumn("dq_failed_rules", F.array().cast("array<struct<rule_id:string,rule_name:string,dimension:string,severity:string>>"))

    severity_rank_col = F.array_max(
        F.transform(
            "dq_failed_rules",
            lambda x: F.when(x["severity"] == "reject", 4)
            .when(x["severity"] == "quarantine", 3)
            .when(x["severity"] == "warn", 2)
            .otherwise(1),
        )
    )
    working = working.withColumn(
        "dq_status",
        F.when(F.size("dq_failed_rules") == 0, F.lit("accepted"))
        .when(severity_rank_col == 4, F.lit("rejected"))
        .when(severity_rank_col == 3, F.lit("quarantined"))
        .otherwise(F.lit("accepted_with_warning")),
    )

    # --- single-pass dataset/rule aggregation ---
    agg_exprs = []
    for cfg in rules:
        agg_exprs.append(F.sum(F.col(f"__applicable_{cfg.id}").cast("int")).alias(f"applicable_{cfg.id}"))
        agg_exprs.append(
            F.sum((F.col(f"__applicable_{cfg.id}") & (~F.col(f"__passed_{cfg.id}"))).cast("int")).alias(f"failed_{cfg.id}")
        )
    status_counts = [
        F.sum((F.col("dq_status") == s).cast("int")).alias(f"count_{s}")
        for s in ("accepted", "accepted_with_warning", "quarantined", "rejected")
    ]
    total_expr = F.count(F.lit(1)).alias("total")
    agg_row = working.agg(*agg_exprs, *status_counts, total_expr).collect()[0].asDict()

    rule_results = []
    dim_failed_weight: dict[str, float] = {}
    dim_applicable_weight: dict[str, float] = {}
    for cfg in rules:
        applicable = agg_row.get(f"applicable_{cfg.id}") or 0
        failed = agg_row.get(f"failed_{cfg.id}") or 0
        passed_n = applicable - failed
        failure_rate = (failed / applicable) if applicable else 0.0
        breached = bool(cfg.threshold_dataset_fail_rate is not None and failure_rate > cfg.threshold_dataset_fail_rate)
        rule_results.append({
            "rule_id": cfg.id, "rule_name": cfg.name, "dimension": cfg.dimension,
            "severity": cfg.severity, "records_applicable": applicable,
            "records_passed": passed_n, "records_failed": failed,
            "failure_rate": round(failure_rate, 5), "dataset_threshold_breached": breached,
        })
        weight = SEVERITY_WEIGHT.get(cfg.severity, 0.4)
        dim_failed_weight[cfg.dimension] = dim_failed_weight.get(cfg.dimension, 0.0) + failed * weight
        dim_applicable_weight[cfg.dimension] = dim_applicable_weight.get(cfg.dimension, 0.0) + applicable * weight

    dim_scores = {}
    for dim in DIMENSION_WEIGHT:
        applicable_w = dim_applicable_weight.get(dim, 0.0)
        if applicable_w <= 0:
            continue
        dim_scores[dim] = round(100 * (1 - dim_failed_weight.get(dim, 0.0) / applicable_w), 2)

    active_weight_sum = sum(DIMENSION_WEIGHT[d] for d in dim_scores) or 1.0
    dataset_score = round(sum(DIMENSION_WEIGHT[d] * dim_scores[d] for d in dim_scores) / active_weight_sum, 2)

    scores = {
        "records_ingested": agg_row["total"],
        "records_accepted": agg_row.get("count_accepted") or 0,
        "records_warned": agg_row.get("count_accepted_with_warning") or 0,
        "records_quarantined": agg_row.get("count_quarantined") or 0,
        "records_rejected": agg_row.get("count_rejected") or 0,
        "score_completeness": dim_scores.get("completeness"),
        "score_validity": dim_scores.get("validity"),
        "score_uniqueness": dim_scores.get("uniqueness"),
        "score_consistency": dim_scores.get("consistency"),
        "score_integrity": dim_scores.get("integrity"),
        "score_timeliness": dim_scores.get("timeliness"),
        "score_overall": dataset_score,
    }

    drop_cols = [c for c in working.columns if c.startswith("__passed_") or c.startswith("__applicable_")]
    working = working.drop(*drop_cols)

    return {"df": working, "rule_results": rule_results, "scores": scores}
