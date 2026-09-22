"""Segment evaluation against PostgreSQL (§14.5): the interactive/SQL backend.

Full recompute each run (ADR-14): no incremental membership maintenance.
Membership is replaced per segment inside one transaction, and the
entered/exited delta is written to the append-only event log.
"""
from __future__ import annotations

from datetime import date

import psycopg
import yaml

from .compiler import compile_ast


def load_segment_defs(path) -> list[dict]:
    return yaml.safe_load(open(path))["segments"]


def evaluate_segment(conn: psycopg.Connection, segment: dict, run_id: int | None = None) -> dict:
    predicate = compile_ast(segment["rule_ast"], segment.get("thresholds", {}), segment.get("null_handling", "exclude"))
    query = f"""
        SELECT c.canonical_customer_id
        FROM customers c
        JOIN customer_metrics cm ON cm.canonical_customer_id = c.canonical_customer_id
        WHERE {predicate.sql}
    """
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO segments (segment_id, name, description, current_version, is_active, created_by)
               VALUES (%s, %s, %s, 1, TRUE, 'system')
               ON CONFLICT (segment_id) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description""",
            (segment["id"], segment["name"], segment["description"]))
        cur.execute(
            """INSERT INTO segment_versions (segment_id, version, rule_ast, thresholds, null_handling, created_by)
               VALUES (%s, 1, %s, %s, %s, 'system')
               ON CONFLICT (segment_id, version) DO UPDATE SET rule_ast = EXCLUDED.rule_ast,
                   thresholds = EXCLUDED.thresholds, null_handling = EXCLUDED.null_handling""",
            (segment["id"], psycopg.types.json.Json(segment["rule_ast"]),
             psycopg.types.json.Json(segment.get("thresholds", {})), segment.get("null_handling", "exclude")))

        cur.execute(query, predicate.params)
        current_members = {row[0] for row in cur.fetchall()}

        cur.execute("SELECT canonical_customer_id FROM segment_members WHERE segment_id = %s", (segment["id"],))
        previous_members = {row[0] for row in cur.fetchall()}

        entered = current_members - previous_members
        exited = previous_members - current_members

        cur.execute("DELETE FROM segment_members WHERE segment_id = %s", (segment["id"],))
        if current_members:
            cur.executemany(
                "INSERT INTO segment_members (segment_id, canonical_customer_id, definition_version, entered_on, run_id) "
                "VALUES (%s, %s, 1, %s, %s)",
                [(segment["id"], cid, date.today(), run_id) for cid in current_members])

        for cid in entered:
            cur.execute(
                "INSERT INTO segment_membership_events (segment_id, canonical_customer_id, change_type, reason, "
                "definition_version, run_id) VALUES (%s, %s, 'entered', 'data_change', 1, %s)",
                (segment["id"], cid, run_id))
        for cid in exited:
            cur.execute(
                "INSERT INTO segment_membership_events (segment_id, canonical_customer_id, change_type, reason, "
                "definition_version, run_id) VALUES (%s, %s, 'exited', 'data_change', 1, %s)",
                (segment["id"], cid, run_id))

        cur.execute(
            "INSERT INTO segment_run_stats (segment_id, run_id, definition_version, member_count, entered_count, exited_count) "
            "VALUES (%s, %s, 1, %s, %s, %s)",
            (segment["id"], run_id, len(current_members), len(entered), len(exited)))
    conn.commit()
    return {"segment_id": segment["id"], "member_count": len(current_members),
            "entered": len(entered), "exited": len(exited)}


def evaluate_all(conn: psycopg.Connection, segments_config_path, run_id: int | None = None) -> list[dict]:
    return [evaluate_segment(conn, seg, run_id) for seg in load_segment_defs(segments_config_path)]
