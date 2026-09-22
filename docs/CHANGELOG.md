# Changelog

Built in dependency order in a single continuous session, each entry
corresponding to a commit on `claude/vibrant-einstein-r1v8h1`.

- **Repository foundation & synthetic data generator** — seeded PCG64
  population model, purchase/session/ticket/marketing synthesis, defect
  injection for all 35 seeded defects in §4.9, manifest + identity ground
  truth. Verified byte-identical output across repeated runs.
- **Dataset schema contracts + PostgreSQL serving schema** — contract
  model for all nine source datasets; Alembic migration for the full
  serving data model (34 tables: core domain, analytical, operational).
  Verified against a live PostgreSQL 16 instance.
- **PySpark ingestion/typing/cleaning + DQ rule engine** — all-string raw
  read with lineage, contract-driven typing, identifier normalisation, a
  generic 18-rule-type DQ engine with 40 configured rules across six
  dimensions. Verified end-to-end against real generated data for all
  seven tabular/JSON datasets.
- **Identity resolution engine** — namespaced screening, ranked match
  rules, iterative connected components, cluster guards, canonical-ID
  stability with a merge/split audit trail. Verified against all of
  §10.8's hand-built worked examples.
- **Aggregation, loader, orchestration, segmentation** — order enrichment,
  RFM/CLV/churn metrics, sessionisation, a COPY-based upsert loader, a
  13-stage orchestration CLI with per-stage run bookkeeping, and a
  parameterised-SQL segment rule compiler with the 8 baseline segments.
  Verified end-to-end into a live PostgreSQL instance.
- **FastAPI backend** — JWT + Argon2id + RBAC, server-side PII masking,
  DB-backed endpoints for auth/customers/segments/analytics/quality/
  pipeline/health. 9 API integration tests passing.
- **React + TypeScript console** — 9 screens on an enterprise
  graphite/teal design system, verified with a headless Playwright smoke
  test against the live backend.
- **Bug fix: identity ground-truth desync + inexact frequency screening**
  — found while producing the honest identity evaluation the plan
  requires; see ADR-15/ADR-16 in `PROJECT_DECISIONS.md`. Improved measured
  pairwise precision from ~0.27 (an artifact of the ground-truth bug) to
  0.994 with the fixes in place.
- **Docker Compose, CI, Makefile, documentation** — this pass.
