"""Identity resolution evaluation against generator ground truth (§10.9).

Reads ``ground_truth_identity.{parquet,csv}`` (never consumed by the
pipeline itself) and the resolved ``customer_identities`` table, and
computes pairwise precision/recall/F1 over *blocked* pairs -- pairs that
share either a true_person_id or a resolved canonical_customer_id -- never
by materialising all N^2 pairs.
"""
from __future__ import annotations

import itertools
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd
import psycopg


def _load_ground_truth(generated_dir: Path) -> pd.DataFrame:
    parquet_path = generated_dir / "ground_truth_identity.parquet"
    csv_path = generated_dir / "ground_truth_identity.csv"
    if parquet_path.exists():
        return pd.read_parquet(parquet_path)
    return pd.read_csv(csv_path)


def _pairs(members: list[str]) -> set[tuple[str, str]]:
    return {tuple(sorted(p)) for p in itertools.combinations(sorted(members), 2)}


def evaluate(generated_dir: Path, database_url: str) -> dict:
    truth = _load_ground_truth(generated_dir)
    truth["source_record_key"] = truth["source_system"] + ":" + truth["source_record_id"]

    conn = psycopg.connect(database_url)
    resolved = pd.read_sql(
        "SELECT source_system, source_record_id, canonical_customer_id FROM customer_identities", conn)
    conn.close()
    resolved["source_record_key"] = resolved["source_system"] + ":" + resolved["source_record_id"]

    merged = truth.merge(resolved, on="source_record_key", how="inner")

    true_groups: dict[str, list[str]] = defaultdict(list)
    resolved_groups: dict[str, list[str]] = defaultdict(list)
    for _, row in merged.iterrows():
        true_groups[row["true_person_id"]].append(row["source_record_key"])
        resolved_groups[row["canonical_customer_id"]].append(row["source_record_key"])

    true_pairs: set[tuple[str, str]] = set()
    for members in true_groups.values():
        true_pairs |= _pairs(members)

    resolved_pairs: set[tuple[str, str]] = set()
    for members in resolved_groups.values():
        resolved_pairs |= _pairs(members)

    tp = len(true_pairs & resolved_pairs)
    fp = len(resolved_pairs - true_pairs)
    fn = len(true_pairs - resolved_pairs)

    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    over_merged = sum(1 for members in resolved_groups.values()
                       if len({truth.set_index("source_record_key").loc[m, "true_person_id"] for m in members
                               if m in truth["source_record_key"].values}) > 1)
    under_merged = sum(1 for members in true_groups.values()
                        if len({resolved.set_index("source_record_key").loc[m, "canonical_customer_id"] for m in members
                                if m in resolved["source_record_key"].values}) > 1)

    return {
        "true_pairs": len(true_pairs), "resolved_pairs": len(resolved_pairs),
        "true_positive_pairs": tp, "false_positive_pairs": fp, "false_negative_pairs": fn,
        "pairwise_precision": round(precision, 4), "pairwise_recall": round(recall, 4), "f1": round(f1, 4),
        "over_merge_incidents": over_merged, "under_merge_incidents": under_merged,
        "evaluated_source_records": len(merged),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--generated-dir", required=True)
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args()
    result = evaluate(Path(args.generated_dir), args.database_url)
    print(json.dumps(result, indent=2))
