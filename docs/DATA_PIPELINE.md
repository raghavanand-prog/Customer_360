# Data Pipeline

Entry point: `backend/c360/pipeline/run_pipeline.py`, a Typer CLI. One
Spark session per run (`c360.spark.session.build_spark`), configuration
per §8.1 (`spark.sql.adaptive.*` on, explicit broadcast threshold, UTC
session timezone, dynamic partition overwrite mode).

## Stages, in order

| # | Stage | Module | What it does |
|---|---|---|---|
| 1-8 | `ingest_type_clean_<dataset>` | `pipeline/readers.py`, `pipeline/typing_clean.py`, `dq/engine.py` | Per dataset: all-string read + lineage → contract-typed (`try_cast`) → cleaned/normalised → DQ-evaluated → filtered to `accepted`/`accepted_with_warning` |
| 9 | `identity_resolve` | `pipeline/conform.py`, `identity/resolve.py` | Build the namespaced identifier long table from CRM/loyalty/app, screen, match, cluster, guard, assign canonical IDs |
| 10 | `load_customers_and_identity` | `run_pipeline.py`, `loader/postgres_loader.py` | Attribute-precedence resolution (CRM > loyalty > app) for name/email/phone/city/state; upsert `customers` and `customer_identities` |
| 11 | `attribute_orders` | `pipeline/conform.py::resolve_order_customer_ref` | Resolve each order's polymorphic `customer_ref` (a CRM ID, an app user ID, or an email — inferred from shape when `customer_ref_type` is missing) to a canonical customer via the identity lookup table |
| 12 | `load_orders` | `loader/postgres_loader.py` | Dedup exact-duplicate orders (F-05, keyed on `order_id`, kept by latest `updated_at`) then upsert `orders` |
| 13 | `aggregate_customer_metrics` | `pipeline/aggregate.py::compute_customer_metrics` | RFM via `NTILE(5)`, `churn_risk_band` thresholds, `historical_clv`, engagement score; upsert `customer_metrics` |

Every stage writes a row to `pipeline_stage_runs` with status, row counts,
and duration, inside `StageTimer` (`run_pipeline.py`); a failure rolls back
its own transaction and marks the run `failed` without touching earlier
committed stages.

## DQ engine mechanics (§9)

`c360/dq/engine.py::evaluate` compiles every configured rule
(`config/dq_rules.yaml`, 40 rules across the six dimensions) to a Spark
`Column` expression via the `RULE_REGISTRY` in `c360/dq/rules.py`, adds one
`__passed_<rule_id>`/`__applicable_<rule_id>` column pair per rule, and
computes the per-record `dq_failed_rules` array and `dq_status`
(`accepted`/`accepted_with_warning`/`quarantined`/`rejected`) in a single
pass. All rule-result counts (applicable/failed per rule, plus dataset-wide
status counts) are gathered in **one** `agg()` call per dataset — not one
`count()` per metric, per the "minimise actions" requirement in §8.3.

## Identity resolution mechanics (§10)

See `docs/ARCHITECTURE.md` for the scaling argument and
`benchmarks/IDENTITY_EVAL.md` for measured precision/recall. In brief:
`screening.py` (S1-S5 guards) → `matching.py` (R-01..R-04 edges via
groupBy-blocking) → `components.py` (iterative min-label-propagation
connected components, `localCheckpoint`ed every iteration, non-convergence
raises) → `guards.py` (max cluster size, minimum path confidence,
attribute-conflict — driver-side union-find on the offending cluster's
own edges only) → `canonical.py` (cross-run stable ID assignment via
merge/split resolution against the prior run's `member_to_canonical`
mapping).

**Not implemented in this build:** R-05 (order-reference identity edges)
and R-06 (email-local-part + phone-last-6 review candidate) as
edge-generating rules for *clustering* — order attribution instead uses a
direct lookup against the resolved identity graph
(`resolve_order_customer_ref` + `identity_lookup` join in
`run_pipeline.py`), which achieves the same practical outcome (orders
attach to the right customer) without adding orders as vertices in the
identity graph itself. The dual SQL/Spark segment-compiler backend (§14.4)
is also SQL-only in this build. Both are recorded as ADRs in
`docs/PROJECT_DECISIONS.md`.

## Transformations vs actions (§8.3)

`typing_clean.py` and `dq/engine.py` accumulate 30+ column expressions
(cast, trim, regex, coalesce) before a single write/collect triggers
execution — Catalyst fuses the chain into one physical pass, which is
directly observable by running `.explain()` on the resulting DataFrame
(not captured to a committed file in this session, unlike the plan's
request in §8.3, due to time).

## Idempotency

Orders and customer_metrics are upserted on their natural/canonical key
(`ON CONFLICT ... DO UPDATE`), so re-running the pipeline on unchanged
input does not duplicate rows. Canonical customer IDs are stable across
runs by construction (`c360/identity/canonical.py`) — re-running twice on
identical input yields identical IDs, proven by
`test_identity_resolution.py::test_two_runs_on_unchanged_input_produce_identical_canonical_ids`.
