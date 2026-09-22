# Benchmark Results

Real measurements only, per §25.6 of `PROJECT_PLAN.md` — nothing here is
estimated. Every number is read directly from `pipeline_stage_runs` for a
committed run ID, or from a direct `curl -w` timing.

## Environment

- Single-container Spark local mode (`local[*]`), PostgreSQL 16, both on
  the same host (a sandboxed development container: 4 vCPU class, no GPU).
- These are **not** representative of the `large` (500k-person) profile,
  which was not run in this environment for lack of time — see
  "What was not measured" below. Treat everything here as `tiny`/`small`
  profile numbers only.

## Pipeline stage durations — `small` profile (1,000 persons), run #8

| Stage | Rows in | Rows out | Duration |
|---|---:|---:|---:|
| ingest_type_clean_customers_crm | 563 | 550 | 8.19 s |
| ingest_type_clean_loyalty_members | 404 | 401 | 2.11 s |
| ingest_type_clean_app_users | 594 | 594 | 1.85 s |
| ingest_type_clean_products | 500 | 494 | 1.61 s |
| ingest_type_clean_orders | 2,712 | 2,706 | 1.79 s |
| ingest_type_clean_order_items | 6,125 | 6,071 | 1.16 s |
| ingest_type_clean_support_tickets | 159 | 153 | 1.20 s |
| ingest_type_clean_marketing_events | 19,390 | 19,390 | 0.83 s |
| **identity_resolve** | 3,977 edges-input rows | 991 canonical customers | **59.0 s** |
| load_customers_and_identity | — | 2,536 rows upserted | 1.26 s |
| attribute_orders | — | 2,679 | 0.99 s |
| load_orders | — | 2,679 rows upserted | 1.02 s |
| aggregate_customer_metrics | — | 485 rows | 3.10 s |
| **Total (excluding Spark session startup)** | | | **~83 s** |

**Reading this honestly.** `identity_resolve` dominates the run at this
profile — not because the data volume is large (3,977 edge-input rows is
tiny), but because Spark's per-iteration overhead (planning, a shuffle, a
`localCheckpoint`) is paid on every one of the connected-components loop's
iterations regardless of data size, and `local[*]` on a small container
adds JVM/driver overhead on top. This is the single most useful thing this
harness demonstrates: the fixed cost of the iterative-join algorithm is the
thing to optimise for at moderate scale, not row throughput — exactly the
kind of scaling behaviour §25.4 asks this project to be honest about
instead of hand-waving.

## API latency (informal, `curl -w`, warm, `small`-profile data loaded)

| Endpoint | Observed |
|---|---:|
| `GET /api/v1/health` | < 10 ms |
| `POST /api/v1/auth/login` | ~90 ms (Argon2id hashing dominates, by design) |
| `GET /api/v1/analytics/summary` | ~15 ms |
| `GET /api/v1/customers/{id}/profile` | ~20 ms |

These are single-request, single-user observations from one local run —
not a load test. A proper concurrent-load benchmark (`locust` or `k6`
against the `medium` profile) is listed as future work in
`docs/PROJECT_DECISIONS.md` rather than approximated here.

## What was not measured (stated explicitly, per §35/§37)

- The `medium` (50,000-person, ~5M-event) and `large` (500,000-person,
  ~50M-event) profiles were **not generated or run** in this environment.
  Generating and benchmarking them requires materially more time and disk
  than was available in this session. The pipeline and schema are written
  to the same contracts regardless of size profile, but the `large`-profile
  numbers §2.2 (G-30) asks for are genuinely absent here, not estimated.
- No concurrent-load API benchmark was run.
- `docker compose up` was not executed end-to-end in this environment
  (no Docker daemon available in the sandbox this was built in); the
  Compose file was validated with `docker compose config` and every image
  it builds uses the same dependency versions already exercised by the
  test suite and the manual pipeline/API runs recorded above.
