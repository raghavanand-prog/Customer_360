# Data Dictionary

Authoritative DDL: `backend/alembic/versions/0001_initial_schema.py`. This
document is the human-readable companion — for the exact column list, type,
and constraint of any table, read the migration directly; it is the source
of truth `scripts/check_contracts.py`-style drift checks would compare
against (that check itself was not built — see `PROJECT_DECISIONS.md`).

## Sensitivity labels (§18.6)

| Label | Meaning | Examples | API handling |
|---|---|---|---|
| `internal` | No masking required | `account_status`, `order_status`, `category_id` | Returned as-is |
| `pii` | Personally identifying | `primary_email`, `primary_phone`, `city` | Masked server-side for `viewer`/`analyst` roles (`c360/security/masking.py`) |
| `sensitive_pii` | Higher-sensitivity personal data | `date_of_birth`, `gender`, `marketing_opt_in` | Not currently returned by any endpoint (excluded from response schemas rather than masked) |

## Core domain

| Table | Grain | Key columns | Notes |
|---|---|---|---|
| `customers` | 1 row per canonical customer | `canonical_customer_id` (TEXT, `CX` + sha256 prefix) | Attribute precedence: CRM > loyalty > app (§11.3), resolved in `run_pipeline.py`'s `load_customers_and_identity` stage |
| `customer_identities` | 1 row per (source record, resolved canonical id) | `identity_id` | `identity_namespace='resolved'` in this implementation — see `PROJECT_DECISIONS.md` for why the fuller per-namespace/per-rule provenance row shape described in §10 was simplified for the loader |
| `customer_metrics` | 1 row per customer | `canonical_customer_id` | RFM via `NTILE(5)`, `churn_risk_band` thresholds in `c360/pipeline/aggregate.py` |
| `orders` | 1 row per order | `order_id` | `net_amount`/`revenue_amount` computed in `enrich_orders()`; refunds excluded from `revenue_amount` |
| `order_items` | 1 row per order line | `(order_id, line_number)` | Not populated by the current loader (see `PROJECT_DECISIONS.md`) |
| `products` | 1 row per SKU | `product_id` | Loaded by the DQ/typing pipeline but not yet upserted into PostgreSQL by `run_pipeline.py` |
| `sessions`, `web_events`, `anonymous_events` | Session / event | `session_id` / `event_id` | Schema and sessionisation logic (`c360/pipeline/aggregate.py::sessionise`) are implemented and tested; not wired into the end-to-end loader run in this session (§ scope) |
| `support_tickets`, `marketing_events` | Ticket / marketing touch | `ticket_id` / `marketing_event_id` | Typed and DQ-scored by the pipeline; not yet loaded to PostgreSQL |

## Analytical / serving (denormalised, disposable)

`agg_revenue_daily`, `agg_revenue_monthly`, `agg_cohort_retention`,
`agg_product_performance`, `agg_category_performance`,
`customer_category_affinity`, `product_co_purchase`,
`customer_event_metrics` — all defined in the DDL, all rebuilt-per-run by
design; the analytics endpoints in `c360/repositories/analytics.py` compute
directly from `orders`/`customer_metrics` rather than reading from these
pre-aggregated tables (a valid simplification for the data volumes tested
here — see `PROJECT_DECISIONS.md`).

## Operational / metadata

| Table | Purpose |
|---|---|
| `pipeline_runs`, `pipeline_stage_runs` | Run/stage lifecycle, timings, record counts — populated by every `run_pipeline.py` run |
| `ingestion_files` | Per-file lineage/idempotency (defined; not yet written by the loader) |
| `data_quality_results`, `data_quality_rule_results` | Per-run DQ scores and per-rule pass/fail — fully populated every run |
| `quarantined_records` | Individual failing records with reasons (defined; the DQ engine computes `dq_failed_rules` per record but the loader does not yet persist quarantined rows here — see `PROJECT_DECISIONS.md`) |
| `dedup_audit`, `identity_merge_audit`, `identity_screened_identifiers`, `identity_review_queue`, `identity_crosswalk` | Identity resolution audit trail (defined; the resolver computes this data in-memory — `IdentityResolutionResult.merge_audit_rows`, `.review_queue_rows` — but persistence of these specific tables was not wired into the loader in this session) |
| `segments`, `segment_versions`, `segment_members`, `segment_membership_events`, `segment_run_stats` | Fully implemented and populated by `c360/segments/evaluator.py` |
| `users`, `roles`, `user_roles`, `refresh_tokens`, `audit_logs`, `jobs` | Auth/RBAC/audit — fully implemented and used by the API |

**Reading the gaps above honestly:** the Spark pipeline computes correct
results for every table listed as "defined; not yet written" — the
transformation logic exists and is exercised by the pipeline run
(`web_events`, `order_items`, `quarantined_records` payloads, and the
identity audit trail are all real in-memory Spark/Python results — see
`c360/pipeline/aggregate.py`, `c360/dq/engine.py`, `c360/identity/resolve.py`)
— but the loader stage in `run_pipeline.py` upserts a working subset
(`customers`, `customer_identities`, `orders`, `customer_metrics`) rather
than every table, for time. Extending the loader to the remaining tables is
mechanical (the same `upsert_dataframe()` call against a different
DataFrame) and is the highest-value next step listed in
`PROJECT_DECISIONS.md`.
