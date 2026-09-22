"""Pipeline orchestration CLI (C-02): the stage DAG, run registry, loader.

Deliberately a plain Python/Typer script rather than Airflow/Prefect --
ADR-05 in docs/PROJECT_DECISIONS.md records why: ~10 stages, one schedule,
one executor, no backfill/SLA requirements.
"""
from __future__ import annotations

import time
from datetime import date, datetime, timezone
from pathlib import Path

import psycopg
import typer
import yaml
from pyspark.sql import functions as F

from c360.dq.engine import evaluate, load_ruleset, rules_for_dataset
from c360.identity.resolve import resolve_identities
from c360.pipeline.aggregate import compute_customer_metrics, enrich_orders, sessionise
from c360.pipeline.conform import person_identity_edges, resolve_order_customer_ref
from c360.pipeline.readers import read_raw
from c360.pipeline.typing_clean import apply_cleaning, apply_contract_typing
from c360.schema.datasets import ALL_CONTRACTS
from c360.spark.session import build_spark

app = typer.Typer(add_completion=False)

TABULAR_DATASETS = ["customers_crm", "loyalty_members", "app_users", "products",
                     "orders", "order_items", "support_tickets", "marketing_events"]

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_ROOT = REPO_ROOT / "config"


class StageTimer:
    def __init__(self, conn: psycopg.Connection, run_id: int, stage_order: int, name: str):
        self.conn, self.run_id, self.order, self.name = conn, run_id, stage_order, name

    def __enter__(self):
        self.t0 = time.time()
        typer.echo(f"[pipeline] stage {self.order:02d} {self.name} -- starting")
        return self

    def finish(self, rows_in=0, rows_out=0, rows_quarantined=0, rows_rejected=0, metrics=None):
        duration_ms = int((time.time() - self.t0) * 1000)
        with self.conn.cursor() as cur:
            cur.execute(
                """INSERT INTO pipeline_stage_runs
                   (run_id, stage_name, stage_order, status, rows_in, rows_out,
                    rows_quarantined, rows_rejected, started_at, finished_at, duration_ms, metrics)
                   VALUES (%s,%s,%s,'succeeded',%s,%s,%s,%s, now(), now(), %s, %s)""",
                (self.run_id, self.name, self.order, rows_in, rows_out, rows_quarantined,
                 rows_rejected, duration_ms, psycopg.types.json.Json(metrics or {})),
            )
        self.conn.commit()
        typer.echo(f"[pipeline] stage {self.order:02d} {self.name} -- done in {duration_ms}ms")

    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None:
            self.conn.rollback()
            with self.conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO pipeline_stage_runs (run_id, stage_name, stage_order, status,
                       started_at, finished_at, error_message) VALUES (%s,%s,%s,'failed', now(), now(), %s)""",
                    (self.run_id, self.name, self.order, str(exc)))
            self.conn.commit()
        return False


@app.command()
def run(
    input_dir: str = typer.Option(..., help="Path to data/input (generator output)."),
    dataset_size: str = typer.Option("small"),
    database_url: str = typer.Option(..., envvar="DATABASE_URL"),
    triggered_by: str = typer.Option("cli"),
) -> None:
    conn = psycopg.connect(database_url, autocommit=False)
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO pipeline_runs (pipeline_name, dataset_size, status, triggered_by, started_at)
               VALUES ('c360_pipeline', %s, 'running', %s, now()) RETURNING run_id""",
            (dataset_size, triggered_by))
        run_id = cur.fetchone()[0]
    conn.commit()
    typer.echo(f"[pipeline] run_id={run_id}")

    spark = build_spark(f"c360-pipeline-run-{run_id}")
    dq_config = load_ruleset(CONFIG_ROOT / "dq_rules.yaml")
    input_root = Path(input_dir)
    order_idx = 1

    try:
        typed_clean: dict[str, "DataFrame"] = {}
        for dataset in TABULAR_DATASETS:
            with StageTimer(conn, run_id, order_idx, f"ingest_type_clean_{dataset}") as st:
                order_idx += 1
                df = read_raw(spark, dataset, input_root, run_id)
                rows_in = df.count()
                contract = ALL_CONTRACTS[dataset]
                df = apply_contract_typing(df, contract)
                df = apply_cleaning(df)
                rules = rules_for_dataset(dq_config, dataset)
                if rules:
                    result = evaluate(df, dataset, rules)
                    df = result["df"]
                    with conn.cursor() as cur:
                        cur.execute(
                            """INSERT INTO data_quality_results (run_id, dataset, records_ingested,
                               records_accepted, records_warned, records_quarantined, records_rejected,
                               score_completeness, score_validity, score_uniqueness, score_consistency,
                               score_integrity, score_timeliness, score_overall, ruleset_hash)
                               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING dq_result_id""",
                            (run_id, dataset, result["scores"]["records_ingested"],
                             result["scores"]["records_accepted"], result["scores"]["records_warned"],
                             result["scores"]["records_quarantined"], result["scores"]["records_rejected"],
                             result["scores"]["score_completeness"], result["scores"]["score_validity"],
                             result["scores"]["score_uniqueness"], result["scores"]["score_consistency"],
                             result["scores"]["score_integrity"], result["scores"]["score_timeliness"],
                             result["scores"]["score_overall"], "3"),
                        )
                        dq_result_id = cur.fetchone()[0]
                        for r in result["rule_results"]:
                            cur.execute(
                                """INSERT INTO data_quality_rule_results (dq_result_id, rule_id, rule_name,
                                   dimension, severity, records_applicable, records_passed, records_failed,
                                   failure_rate, dataset_threshold_breached) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                                (dq_result_id, r["rule_id"], r["rule_name"], r["dimension"], r["severity"],
                                 r["records_applicable"], r["records_passed"], r["records_failed"],
                                 r["failure_rate"], r["dataset_threshold_breached"]))
                    conn.commit()
                    df = df.filter(F.col("dq_status").isin("accepted", "accepted_with_warning"))
                typed_clean[dataset] = df.cache()
                st.finish(rows_in=rows_in, rows_out=df.count())

        with StageTimer(conn, run_id, order_idx, "identity_resolve") as st:
            order_idx += 1
            edges, person_attrs = person_identity_edges(
                typed_clean["customers_crm"], typed_clean["loyalty_members"], typed_clean["app_users"])
            rules_cfg = yaml.safe_load((CONFIG_ROOT / "identity_rules.yaml").read_text())
            denylist_cfg = yaml.safe_load((CONFIG_ROOT / "identity_denylist.yaml").read_text())
            id_result = resolve_identities(spark, edges, person_attrs, denylist_cfg, rules_cfg, run_id)
            identities = id_result.customer_identities.cache()
            n_identities = identities.count()
            n_customers = identities.select("canonical_customer_id").distinct().count()
            st.finish(rows_in=edges.count(), rows_out=n_customers,
                      metrics={"source_records": n_identities, "canonical_customers": n_customers,
                               "review_queue_size": len(id_result.review_queue_rows)})

        with StageTimer(conn, run_id, order_idx, "load_customers_and_identity") as st:
            order_idx += 1
            from c360.loader.postgres_loader import upsert_dataframe

            customers_pdf = identities.select("canonical_customer_id").distinct().toPandas()
            customers_pdf["first_name"] = None
            customers_pdf["last_name"] = None
            customers_pdf["full_name_display"] = None
            customers_pdf["primary_email"] = None
            customers_pdf["primary_phone"] = None
            customers_pdf["city"] = None
            customers_pdf["state"] = None
            customers_pdf["country_code"] = "IN"
            customers_pdf["account_status"] = "active"
            customers_pdf["source_system_count"] = 1
            customers_pdf["identity_confidence"] = 0.95
            customers_pdf["needs_review"] = False
            customers_pdf["last_activity_at"] = None
            customers_pdf["last_updated_run_id"] = run_id
            n1 = upsert_dataframe(conn, customers_pdf, "customers", ["canonical_customer_id"])
            conn.commit()

            identities_pdf = identities.toPandas()
            identities_pdf = identities_pdf.rename(columns={
                "source_record_key": "source_record_id__unused"})[
                ["source_system", "source_record_id", "canonical_customer_id"]]
            identities_pdf["identity_namespace"] = "resolved"
            identities_pdf["identity_value_norm"] = None
            identities_pdf["identity_value_hash"] = identities_pdf["source_system"] + ":" + identities_pdf["source_record_id"]
            identities_pdf["identity_value_masked"] = None
            identities_pdf["linked_by_rule"] = None
            identities_pdf["confidence"] = None
            identities_pdf["is_primary"] = False
            identities_pdf["is_screened"] = False
            identities_pdf["identity_id"] = range(1, len(identities_pdf) + 1)
            n2 = upsert_dataframe(conn, identities_pdf, "customer_identities", ["identity_id"])
            conn.commit()
            st.finish(rows_out=n1 + n2)

        with StageTimer(conn, run_id, order_idx, "attribute_orders") as st:
            order_idx += 1
            identity_lookup = edges.join(identities, on=["source_system", "source_record_id"]) \
                .select("identity_namespace", "identity_value_norm", "canonical_customer_id").distinct()

            from pyspark.sql import Window as _W
            dedup_w = _W.partitionBy("order_id").orderBy(F.col("updated_at_typed").desc())
            deduped_orders = (typed_clean["orders"]
                               .withColumn("_rn", F.row_number().over(dedup_w))
                               .filter(F.col("_rn") == 1).drop("_rn"))
            orders_with_ref = resolve_order_customer_ref(deduped_orders)
            orders_attributed = orders_with_ref.join(
                identity_lookup,
                (orders_with_ref.ref_namespace == identity_lookup.identity_namespace)
                & (orders_with_ref.ref_value_norm == identity_lookup.identity_value_norm),
                "left",
            )
            orders_enriched = enrich_orders(orders_attributed)
            st.finish(rows_out=orders_enriched.count())

        with StageTimer(conn, run_id, order_idx, "load_orders") as st:
            order_idx += 1
            from c360.loader.postgres_loader import upsert_dataframe

            orders_pdf = orders_enriched.select(
                F.col("order_id"), F.col("canonical_customer_id"), F.col("customer_ref").alias("source_customer_ref"),
                F.col("customer_ref_type").alias("source_customer_ref_type"), F.col("order_ts_typed").alias("order_ts"),
                F.col("order_status"), F.col("order_type"), F.col("currency"), F.col("gross_amount_typed").alias("gross_amount"),
                F.coalesce(F.col("discount_amount_typed"), F.lit(0)).alias("discount_amount"),
                F.coalesce(F.col("shipping_amount_typed"), F.lit(0)).alias("shipping_amount"),
                F.coalesce(F.col("tax_amount_typed"), F.lit(0)).alias("tax_amount"),
                F.col("net_amount"), F.col("revenue_amount"), F.col("payment_method"), F.col("channel"),
                F.col("is_first_order"), F.col("days_since_previous_order"),
            ).na.drop(subset=["order_id", "order_ts"]).toPandas()
            orders_pdf["item_count"] = 0
            orders_pdf["ingested_run_id"] = run_id
            orders_pdf["days_since_previous_order"] = orders_pdf["days_since_previous_order"].astype("Int64")
            n = upsert_dataframe(conn, orders_pdf, "orders", ["order_id"])
            conn.commit()
            st.finish(rows_out=n)

        with StageTimer(conn, run_id, order_idx, "aggregate_customer_metrics") as st:
            order_idx += 1
            empty_sessions = spark.createDataFrame([], "canonical_customer_id string, has_add_to_cart boolean, event_count long, session_end_ts timestamp")
            metrics = compute_customer_metrics(orders_enriched, empty_sessions, date.today())
            metrics_pdf = metrics.toPandas()
            metrics_pdf = metrics_pdf.where(metrics_pdf.notnull(), None)
            for c in ["sessions_90d", "cart_abandon_sessions_90d", "events_90d"]:
                if c not in metrics_pdf.columns:
                    metrics_pdf[c] = 0
                metrics_pdf[c] = metrics_pdf[c].fillna(0).astype(int)
            metrics_pdf["tenure_days"] = None
            metrics_pdf["forward_clv_heuristic"] = None
            metrics_pdf["preferred_category_id"] = None
            metrics_pdf["days_since_last_seen"] = metrics_pdf.get("days_since_last_seen")
            from c360.loader.postgres_loader import upsert_dataframe
            cols = ["canonical_customer_id", "as_of_date", "order_count", "total_spend", "refunded_amount",
                    "aov", "first_order_at", "last_order_at", "days_since_last_order", "median_ipi_days",
                    "purchase_frequency_per_year", "historical_clv", "forward_clv_heuristic", "r_score",
                    "f_score", "m_score", "rfm_segment", "sessions_90d", "events_90d", "cart_abandon_sessions_90d",
                    "engagement_raw", "engagement_score", "churn_risk_band", "preferred_category_id", "tenure_days"]
            for c in cols:
                if c not in metrics_pdf.columns:
                    metrics_pdf[c] = None
            n = upsert_dataframe(conn, metrics_pdf[cols], "customer_metrics", ["canonical_customer_id"])
            conn.commit()
            st.finish(rows_out=n)

        with conn.cursor() as cur:
            cur.execute(
                "UPDATE pipeline_runs SET status='succeeded', finished_at=now(), "
                "duration_ms = EXTRACT(EPOCH FROM (now() - started_at)) * 1000 WHERE run_id=%s", (run_id,))
        conn.commit()
        typer.echo(f"[pipeline] run {run_id} succeeded")
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE pipeline_runs SET status='failed', finished_at=now(), error_summary=%s WHERE run_id=%s",
                (str(exc)[:1000], run_id))
        conn.commit()
        typer.echo(f"[pipeline] run {run_id} FAILED: {exc}", err=True)
        raise
    finally:
        spark.stop()
        conn.close()


if __name__ == "__main__":
    app()
