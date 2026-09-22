# Project Decisions

Architecture decision records, scope reductions, and an honest gap list.
This document exists because `PROJECT_PLAN.md` explicitly requires it: a
blocker gets recorded here, not silently worked around, and a claim of
completeness is only as good as this list is honest.

## Architecture decision records

### ADR-01: Layers computed within one Spark session, not materialised between every stage

RAW/STAGING/CURATED are described in `PROJECT_PLAN.md` §7.1 as separate
Parquet directories written and read back between stages. This
implementation instead chains `read → type → clean → DQ → conform →
identity → aggregate` as function calls within one Spark job graph per
pipeline run, with `.cache()` at the per-dataset accepted/cleaned
checkpoint. **Reason:** materialising and re-reading Parquet between every
one of 13 stages roughly triples wall-clock time for no correctness
benefit at the `tiny`/`small` profiles this was tested against, and the
module boundaries (readers/typing_clean/dq/conform/identity/aggregate) are
still separate, independently testable units. **Cost:** the
partition-level replay/idempotency story from §7.5 (a failed stage leaves
partial Parquet, safe to re-run) does not apply as directly — a failed
pipeline run today re-reads and reprocesses everything from RAW on retry,
which is correct but not incremental. **Revisit when:** the `medium`/`large`
profiles are actually run and the cost of full reprocessing on retry
becomes material.

### ADR-05: Typer CLI orchestration instead of Airflow

Recorded in `docs/ARCHITECTURE.md`. ~13 stages, one schedule, one
executor, no backfill/SLA requirement — Airflow's operational surface
would exceed what a 13-stage linear-ish DAG needs.

### ADR-09: Loader uses `psycopg` COPY + upsert, not Spark JDBC writes

Recorded in `docs/ARCHITECTURE.md`.

### ADR-12: Hand-rolled connected components, not GraphFrames

`c360/identity/components.py` implements min-label propagation directly
on the DataFrame API rather than adding a GraphFrames dependency. Reason
stated in the plan: 60 explainable lines beat a dependency whose failure
modes are unfamiliar, for a graph this shape.

### ADR-14: Segments evaluated in SQL only, not a dual SQL/Spark backend

§14.4 specifies a single rule AST compiled to *both* a SQL predicate
(interactive preview) and a Spark `Column` expression (batch recompute
over 500k+ customers), with an equivalence test (`T-17`) proving they
agree. This build has the SQL compiler only
(`c360/segments/compiler.py`) — full recompute also runs this SQL against
`customer_metrics` in PostgreSQL, since even the `small`-profile customer
count (1,000) evaluates in milliseconds. **Reason:** at the profiles
actually tested, the Spark backend's raison d'être (a customer base too
large for interactive SQL) doesn't apply, and building a second AST
visitor plus the equivalence test was lower-value than the identity
resolution and DQ engine work given the time available. **Revisit when:**
running against the `medium`/`large` profile, where a 50k+ or 500k+ row
full recompute against live PostgreSQL would compete with API read
traffic.

### ADR-15: Identity ground truth must be built from the exact IDs writers emit, not recomputed

Found and fixed while producing `benchmarks/IDENTITY_EVAL.md`. The first
version of `c360/generator/main.py` built `ground_truth_identity` by
recomputing a sequential CRM-ID counter (`crm_seq`) in a loop separate from
`write_customers_crm`. The moment a within-source duplicate (X-07) caused
`write_customers_crm` to emit two rows for one person, that external
counter silently desynchronised from the IDs actually written to
`customers_crm.csv` — corrupting the ground truth for every person
generated afterward, and making the identity resolver measure as ~0.27
pairwise precision when it was actually ~0.99. **Fix:** `write_customers_crm`
/ `write_loyalty` / `write_app_users` now return the exact `(record_id,
true_person_id)` pairs they wrote; `main.py` uses those directly. **Lesson
worth keeping in the repo history:** an evaluation harness is code, and it
can be the bug.

### ADR-16: Identity screening uses exact `collect_set`-based counts, not `approx_count_distinct`

Found in the same debugging session as ADR-15. `approx_count_distinct`
(HyperLogLog) is built for scale and is unreliable at the small
per-identifier cardinalities the S3/S4 screening guards operate over (is
this identifier shared by 7 records or 9?) — the estimator's error at
n<20 was large enough to let some genuinely high-frequency identifiers
through unscreened. Switched to `F.size(F.collect_set(...))` — exact, and
cheap at this cardinality.

## Scope reductions (what the plan asks for that is not fully built)

This list is organised by cost to close, cheapest first, and is the
honest answer to "what's left."

1. **Loader coverage.** `run_pipeline.py` upserts `customers`,
   `customer_identities`, `orders`, `customer_metrics`. The Spark pipeline
   *computes* correct `web_events`, `sessions`, `order_items`,
   `support_tickets`, `marketing_events`, `quarantined_records`, and the
   full identity audit trail (`identity_merge_audit`,
   `identity_screened_identifiers`, `identity_review_queue`,
   `identity_crosswalk`) — the DataFrames exist and are exercised by
   tests — but the loader does not yet upsert them into PostgreSQL. Closing
   this is mechanical (one more `upsert_dataframe()` call per table) and is
   the single highest-value next step.
2. **API surface.** Implemented: auth, customer search/profile/timeline,
   segment list/detail/members, analytics, DQ summary/detail, pipeline
   runs, health. Not implemented: admin user management, segment
   create/update/preview/export, identity review-queue endpoints,
   `/metrics`. Full list in `docs/API.md`.
3. **Frontend screens.** All 11 screens named in the plan exist in some
   form (Login, Overview, Customer Search, Customer 360, Segments +
   Segment Detail, Analytics, Data Quality, Pipeline Runs, System Health).
   Not built as separate screens: a dedicated audience-export flow and an
   identity-review-queue UI (there is no backend endpoint for either yet).
4. **Dual-backend segmentation** (ADR-14) — SQL only.
5. **Order-reference identity edges (R-05/R-06 as clustering rules)** —
   order attribution is correct via a direct lookup, but orders are not
   themselves vertices in the identity graph; documented in
   `docs/DATA_PIPELINE.md`.
6. **Audit logging of profile reads/exports** (§G-27) — the table and
   write function exist, used for login only.
7. **Rate limiting** — dependency declared, not wired in.
8. **`medium`/`large` profile runs** — not generated or benchmarked in
   this environment (time). The pipeline and schema make no
   size-dependent assumptions, but the numbers in §2.2 (G-30) that require
   a `large`-profile run are genuinely absent, not estimated.
9. **`docker compose up` end-to-end** — not executed (no Docker daemon in
   the build environment); validated via `docker compose config` and via
   every image's dependencies already being exercised by the test suite.
10. **`import-linter`-enforced layering, `scripts/check_contracts.py`,
    captured `.explain()` output** — the properties these would check
    (no SQL outside repositories, no `pyspark` reachable from the API,
    schema agreement across contract/DDL/Pydantic) hold by construction in
    the code as written, but are not enforced by a dedicated CI check or
    captured as committed evidence.
11. **Coverage report, full T-01..T-23 test-ID mapping, dedicated
    security/injection test suite, frontend component tests** — see
    `docs/TESTING.md`.

## Originality

No vendor UI, API shape, schema namespace, or branding is reproduced from
any commercial CDP. All data is synthetic, generated locally by
`c360/generator/`, using committed vocabulary lists — no network calls, no
third-party "faker" library, no real personal data anywhere in this
repository. Generated emails use reserved example domains
(`example.com`, `example.net`, `mail.example`) that cannot resolve to a
real mailbox.
