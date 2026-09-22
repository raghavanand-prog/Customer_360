"""Canonical customer ID assignment and stability across runs (§10.7).

Pure Python over already-materialised cluster/crosswalk dictionaries --
deliberately not Spark here, because the whole point of this step is a
small, auditable decision table that must be easy to defend line by line in
an interview, and cluster counts at any realistic size profile fit in
driver memory once identity resolution has already collapsed the graph.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


def mint_id(cluster_key: str) -> str:
    return "CX" + hashlib.sha256(cluster_key.encode()).hexdigest()[:16]


@dataclass
class CanonicalAssignment:
    member_to_canonical: dict[str, str] = field(default_factory=dict)
    crosswalk_rows: list[dict] = field(default_factory=list)
    audit_rows: list[dict] = field(default_factory=list)


def assign_canonical_ids(
    clusters: dict[str, list[str]],
    prior_member_to_canonical: dict[str, str],
    prior_first_seen_run: dict[str, int],
    run_id: int,
) -> CanonicalAssignment:
    result = CanonicalAssignment()

    # --- Pass A: resolve splits. A prior canonical id whose current members
    # now land in more than one cluster is split; the cluster with the most
    # overlap keeps it, the rest must mint (or inherit a different prior id).
    prior_id_to_clusters: dict[str, dict[str, int]] = {}
    for cluster_key, members in clusters.items():
        for m in members:
            prior = prior_member_to_canonical.get(m)
            if prior is None:
                continue
            prior_id_to_clusters.setdefault(prior, {}).setdefault(cluster_key, 0)
            prior_id_to_clusters[prior][cluster_key] += 1

    prior_id_primary_cluster: dict[str, str] = {}
    for prior_id, cluster_counts in prior_id_to_clusters.items():
        best_cluster = sorted(cluster_counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        prior_id_primary_cluster[prior_id] = best_cluster
        if len(cluster_counts) > 1:
            successors = sorted(cluster_counts.keys())
            result.audit_rows.append({
                "event": "cluster_split", "canonical_customer_id": prior_id,
                "related_canonical_ids": ",".join(successors), "rule_id": None,
                "namespace": None, "value_masked": None, "confidence": None,
            })

    # --- Pass B: assign each cluster its canonical id.
    for cluster_key, members in clusters.items():
        candidate_priors = sorted({
            p for p in (prior_member_to_canonical.get(m) for m in members)
            if p is not None and prior_id_primary_cluster.get(p) == cluster_key
        })

        if not candidate_priors:
            canonical_id = mint_id(cluster_key)
            result.crosswalk_rows.append({
                "prior_canonical_customer_id": canonical_id, "canonical_customer_id": canonical_id,
                "status": "current", "first_seen_run_id": run_id, "merged_in_run_id": None,
            })
        elif len(candidate_priors) == 1:
            canonical_id = candidate_priors[0]
        else:
            # merge: survivor = most member records, then earliest first_seen, then lexicographically smallest
            def sort_key(pid: str):
                member_count = sum(1 for m in members if prior_member_to_canonical.get(m) == pid)
                return (-member_count, prior_first_seen_run.get(pid, run_id), pid)

            ordered = sorted(candidate_priors, key=sort_key)
            canonical_id = ordered[0]
            for loser in ordered[1:]:
                result.crosswalk_rows.append({
                    "prior_canonical_customer_id": loser, "canonical_customer_id": canonical_id,
                    "status": "merged", "first_seen_run_id": prior_first_seen_run.get(loser, run_id),
                    "merged_in_run_id": run_id,
                })
            result.audit_rows.append({
                "event": "cluster_merged", "canonical_customer_id": canonical_id,
                "related_canonical_ids": ",".join(ordered[1:]), "rule_id": None,
                "namespace": None, "value_masked": None, "confidence": None,
            })
            result.crosswalk_rows.append({
                "prior_canonical_customer_id": canonical_id, "canonical_customer_id": canonical_id,
                "status": "current", "first_seen_run_id": prior_first_seen_run.get(canonical_id, run_id),
                "merged_in_run_id": None,
            })

        for m in members:
            result.member_to_canonical[m] = canonical_id

    return result
