"""End-to-end identity resolution orchestration (F-06, J-05)."""
from __future__ import annotations

from dataclasses import dataclass

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from .canonical import CanonicalAssignment, assign_canonical_ids
from .components import connected_components
from .guards import apply_guards
from .matching import build_edges
from .screening import screen_identifiers


@dataclass
class IdentityResolutionResult:
    customer_identities: DataFrame       # source_record_key, canonical_customer_id, namespace, value, confidence, rule
    screened_log: DataFrame
    merge_audit_rows: list[dict]
    review_queue_rows: list[dict]
    canonical_assignment: CanonicalAssignment


def resolve_identities(
    spark: SparkSession,
    identity_edges_input: DataFrame,   # source_system, source_record_id, identity_namespace, identity_value_norm
    person_attrs: DataFrame | None,    # source_system, source_record_id, first_name_norm, last_name_norm
    denylist_cfg: dict,
    rules_cfg: dict,
    run_id: int,
    prior_member_to_canonical: dict[str, str] | None = None,
    prior_first_seen_run: dict[str, int] | None = None,
    checkpoint_dir: str | None = None,
) -> IdentityResolutionResult:
    prior_member_to_canonical = prior_member_to_canonical or {}
    prior_first_seen_run = prior_first_seen_run or {}

    input_with_keys = identity_edges_input.withColumn(
        "source_record_key", F.concat_ws(":", "source_system", "source_record_id"))

    screened, screened_log = screen_identifiers(
        identity_edges_input, denylist_cfg, rules_cfg["screening"], person_attrs)

    edges = build_edges(screened, rules_cfg, person_attrs)

    vertices = input_with_keys.select("source_record_key").distinct()
    labels = connected_components(
        spark, vertices, edges.withColumnRenamed("record_a", "a").withColumnRenamed("record_b", "b")
        .select(F.col("a").alias("record_a"), F.col("b").alias("record_b")),
        max_iterations=rules_cfg["clustering"]["max_iterations"],
        checkpoint_dir=checkpoint_dir,
    )

    clusters: dict[str, list[str]] = {}
    for row in labels.collect():
        clusters.setdefault(row["cluster_key"], []).append(row["source_record_key"])

    guard_result = apply_guards(
        labels, edges,
        max_cluster_size=rules_cfg["clustering"]["max_cluster_size"],
        merge_confidence_threshold=rules_cfg["matching"]["merge_confidence_threshold"],
    )

    assignment = assign_canonical_ids(
        guard_result.accepted_clusters, prior_member_to_canonical, prior_first_seen_run, run_id)

    edges_local = {(r["record_a"], r["record_b"]): r for r in edges.collect()}
    identity_rows = []
    for member, canonical_id in assignment.member_to_canonical.items():
        system, record_id = member.split(":", 1)
        identity_rows.append((system, record_id, member, canonical_id))
    identities_df = spark.createDataFrame(
        identity_rows, ["source_system", "source_record_id", "source_record_key", "canonical_customer_id"])

    review_queue_rows = [{
        "run_id": run_id, "reason": r["reason"], "candidate_cluster_key": r["candidate_cluster_key"],
        "member_record_keys": r["member_record_keys"], "cut_edges": r["cut_edges"],
        "min_edge_confidence": r["min_edge_confidence"], "status": "open",
    } for r in guard_result.review_queue]

    merge_audit_rows = [{**a, "run_id": run_id} for a in assignment.audit_rows]

    return IdentityResolutionResult(
        customer_identities=identities_df,
        screened_log=screened_log,
        merge_audit_rows=merge_audit_rows,
        review_queue_rows=review_queue_rows,
        canonical_assignment=assignment,
    )
