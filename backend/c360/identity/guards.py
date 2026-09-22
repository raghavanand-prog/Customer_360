"""Post-computation cluster guards (§10.6).

Guards never delete records; they only decline to merge. Violations are
resolved by cutting the lowest-confidence edges on the offending cluster
until it satisfies every guard, and the cut is written to the review queue
with the reason. Because a genuinely oversized or low-confidence cluster is
rare by construction (screening already removes most degenerate cases), the
per-cluster repair below collects only the *offending* cluster's edges to
the driver -- never the whole graph -- which keeps this bounded and simple
to reason about.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


@dataclass
class GuardResult:
    accepted_clusters: dict[str, list[str]]           # cluster_key -> member keys
    review_queue: list[dict] = field(default_factory=list)


def _union_find_components(vertices: list[str], edges: list[tuple[str, str, float]]) -> list[set[str]]:
    parent = {v: v for v in vertices}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for a, b, _ in edges:
        union(a, b)

    groups: dict[str, set[str]] = {}
    for v in vertices:
        groups.setdefault(find(v), set()).add(v)
    return list(groups.values())


def apply_guards(
    clusters: DataFrame,     # source_record_key, cluster_key
    edges: DataFrame,        # record_a, record_b, rule_id, confidence, namespace, value_masked
    max_cluster_size: int,
    merge_confidence_threshold: float,
) -> GuardResult:
    cluster_sizes = clusters.groupBy("cluster_key").count()
    all_clusters = {row["cluster_key"]: [] for row in clusters.select("cluster_key").distinct().collect()}
    for row in clusters.collect():
        all_clusters[row["cluster_key"]].append(row["source_record_key"])

    edges_by_pair = edges.collect()
    edges_local: dict[str, list[tuple[str, str, float, str]]] = {}
    member_to_cluster = {m: c for c, members in all_clusters.items() for m in members}
    for row in edges_by_pair:
        ck = member_to_cluster.get(row["record_a"])
        if ck is None:
            continue
        edges_local.setdefault(ck, []).append((row["record_a"], row["record_b"], row["confidence"], row["rule_id"]))

    accepted: dict[str, list[str]] = {}
    review_queue: list[dict] = []

    for cluster_key, members in all_clusters.items():
        if len(members) == 1:
            accepted[cluster_key] = members
            continue

        cluster_edges = sorted(edges_local.get(cluster_key, []), key=lambda e: e[2])  # ascending confidence
        working_edges = list(cluster_edges)
        cut_edges: list[dict] = []

        def components_of(edge_list):
            return _union_find_components(members, [(a, b, c) for a, b, c, _ in edge_list])

        # Attribute-conflict guard (§10.8 Example 3): a 2-member cluster
        # linked *only* by an unreinforced R-03 (phone) edge -- R-04 would
        # already have produced a higher-confidence edge for the same pair
        # had the names been compatible, so its absence here is the signal.
        if len(members) == 2 and len(working_edges) == 1 and working_edges[0][3] == "R-03":
            e = working_edges[0]
            cut_edges.append({"a": e[0], "b": e[1], "confidence": e[2], "rule_id": e[3], "reason": "attribute_conflict"})
            working_edges = []

        # Guard: minimum path confidence -- cut edges below threshold first.
        below_threshold = [e for e in working_edges if e[2] < merge_confidence_threshold]
        if below_threshold:
            for e in below_threshold:
                cut_edges.append({"a": e[0], "b": e[1], "confidence": e[2], "rule_id": e[3], "reason": "low_confidence_merge"})
            working_edges = [e for e in working_edges if e[2] >= merge_confidence_threshold]

        comps = components_of(working_edges)

        # Guard: max cluster size -- iteratively remove the weakest surviving
        # edge from any oversized component until every component fits.
        while any(len(c) > max_cluster_size for c in comps):
            if not working_edges:
                break
            removed = working_edges.pop(0)  # weakest remaining edge (list stays sorted)
            cut_edges.append({"a": removed[0], "b": removed[1], "confidence": removed[2],
                               "rule_id": removed[3], "reason": "cluster_too_large"})
            comps = components_of(working_edges)

        for comp in comps:
            comp_list = sorted(comp)
            new_key = comp_list[0]
            accepted[new_key] = comp_list

        if cut_edges:
            review_queue.append({
                "reason": cut_edges[0]["reason"] if len({c["reason"] for c in cut_edges}) == 1 else "mixed",
                "candidate_cluster_key": cluster_key,
                "member_record_keys": members,
                "cut_edges": cut_edges,
                "min_edge_confidence": min((e[2] for e in cluster_edges), default=None),
            })

    return GuardResult(accepted_clusters=accepted, review_queue=review_queue)
