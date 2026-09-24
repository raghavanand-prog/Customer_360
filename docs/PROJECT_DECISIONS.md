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

### ADR-17: pgvector in the existing Postgres, not a separate vector database

The Customer360 Intelligence Assistant (RAG) needs similarity search over a
small (~70-150 chunk) documentation corpus. Adding a dedicated vector
database (Pinecone, Weaviate, Qdrant, ...) would mean a second data store,
a second connection string, a second set of credentials, and a second
thing that can be down — for a corpus this size, none of that buys
anything a `vector` column and the `<=>` cosine-distance operator in the
Postgres instance this project already runs don't provide. Neon supports
the `pgvector` extension directly. **Revisit when:** the corpus grows into
the tens of thousands of chunks and query latency or index-build time on
Postgres becomes a measured problem — not before, and not speculatively.

### ADR-18: No approximate-nearest-neighbour index at this corpus size

The first version of migration `0003_ai_knowledge` added an `ivfflat`
index with `lists=100`. Verified during development: with only 69 rows,
`ivfflat`'s default `probes=1` silently returned **zero** results for
every query, because most of the 100 list partitions held 0-1 rows and the
single probed list often wasn't one of them. Fixed by removing the
approximate index entirely — a sequential scan over a few hundred rows is
both exact and fast, and there is nothing to gain from an approximate
index until the corpus is large enough (low thousands+) for the trade-off
(index build cost, and precision loss from the number of lists probed) to
actually pay for itself. Left as an explicit `-- Revisit` comment in the
migration rather than a benchmarked constant, since it hasn't been
benchmarked at that scale.

### ADR-19: A fixed keyword router chooses tools, not an LLM-driven planning loop

The assistant's tool selection (`c360/ai/agent.py::route_question`) is a
plain keyword-to-tool lookup table, not a step where an LLM decides which
function to call. Three reasons, in order of importance: (1) **security** —
see `docs/AI_SECURITY.md`; there is no path from adversarial text in a
prompt to an unintended tool call, because the LLM is never given the
ability to choose one; (2) **it works without any LLM configured at all**,
which this environment genuinely has none of, and the whole tool-calling
and retrieval pipeline needed to be end-to-end testable regardless; (3) **it
is 100% deterministic and unit-testable** — see the tool-call-correctness
score in `docs/AI_EVALUATION.md` (12/12 on the eval set), which would not
be a meaningful, reproducible number for an LLM-driven router without a
configured model and a much larger eval set. **Trade-off accepted:** the
router only recognises the keyword patterns it's given; a differently
phrased question that doesn't match any pattern gets only the base
`get_customer_profile` tool (if a customer is in context) rather than a
model reasoning about intent. **Revisit when:** a real LLM is configured
and the keyword router's miss rate on real usage is actually measured
against an LLM-driven alternative — not before.

### ADR-20: A single controlled agent, not an autonomous multi-agent system

The assistant is one bounded call sequence (route → call allowlisted tools
→ retrieve docs → generate) with a hard cap on tool calls
(`MAX_TOOL_CALLS_HARD_CAP = 6`) and no loop where the model re-plans based
on intermediate results. An autonomous or multi-agent design (planner
agent + worker agents, iterative re-querying) would add failure modes
(runaway loops, harder-to-audit tool-call chains, higher latency and cost
once a real LLM is billed per call) with no corresponding capability this
project's actual questions need. **Revisit when:** a real usage pattern
emerges that a single bounded pass genuinely cannot answer (e.g.
multi-step reasoning across several customers) — not speculatively.

### ADR-21: Provider-agnostic LLM/embedding interfaces, with a deterministic local fallback

`c360/ai/llm.py` and `c360/ai/embeddings.py` define small interfaces
(`generate`/`stream`/`structured_generate`; `embed_documents`/
`embed_query`) rather than calling a specific vendor's SDK throughout the
codebase. The concrete reason this mattered in practice, not just in
principle: **no LLM or embedding API key exists anywhere in this project**,
and the feature still had to build, test, and run correctly end-to-end
without one — via `NotConfiguredProvider` and
`DeterministicLocalEmbedding` respectively. Both fallbacks are the *only*
implementations actually exercised in this environment (see
`docs/AI_EVALUATION.md` for exactly what that means for measured
results). A real provider (`AnthropicProvider` exists, code-complete, HTTP
calls only, no added SDK dependency) can be activated purely via an
environment variable with no other code change.

### ADR-22 (finding, not a design decision): segment evaluation was fully written but never wired to anything

Found while making CI genuinely test the new AI feature against a clean
database rather than a long-lived dev database with leftover state.
`c360/segments/evaluator.py::evaluate_all` — the full SQL-backend segment
recompute described in ADR-14 — was complete and correct, but was never
called from `run_pipeline`, the CLI, or the `Makefile`. `segments` and
`segment_members` only ever had rows in this project's dev/Neon databases
because someone (an earlier session) invoked it manually at some point;
`test_api.py::test_segments_list` was consequently passing in CI (and
locally) for the wrong reason — pytest never re-created the data it was
asserting against, it was relying on residual state from previous runs
that happened to persist in whichever database was configured. **Fix:**
added `python -m c360.cli evaluate-segments`, wired into CI right after
the pipeline run. Verified on a genuinely fresh, migrated-but-empty
database: pipeline run → `evaluate-segments` → all 46 tests (25 existing +
21 new AI tests) pass, including `test_segments_list`'s assertion of 8
segments. Recorded here rather than silently fixed, because "a test was
passing for the wrong reason" is exactly the kind of gap this project's
own ADR-15/16 already set the precedent of documenting honestly instead of
hiding.

### ADR-23: Java/Spring/Hibernate, XML integration, and a Node.js gateway are deliberately out of scope for this phase

The Adobe Associate Technical Consultant JD asks for Java/Spring/Hibernate
and XML/web-services experience, and mentions Node.js. None of the three
are implemented in this repository as of this phase. This is a scope
decision, not an oversight: adding a Spring Boot service, an XML export
endpoint, or a Node.js streaming gateway with no real architectural need
(FastAPI already serves the AI endpoint cleanly) would be exactly the
"keyword-collection" outcome this phase's own instructions warned against.
See `docs/ADOBE_JD_ALIGNMENT.md` for these marked honestly as 🔴 Not
implemented, and `docs/ENTERPRISE_JAVA_NOTES.md` (if/when written) for
concept-level interview preparation that doesn't require polluting the
product with code that has no job to do.

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
