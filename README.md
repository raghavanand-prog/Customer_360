# Customer360 — Unified Customer Data & Personalization Platform

A batch-first customer data platform that ingests deliberately messy
customer, transaction, and behavioural data from eight simulated source
systems, validates and quarantines it through a configurable data-quality
engine, resolves fragmented records into canonical customers using an
explainable deterministic identity graph built in PySpark, and serves
unified Customer 360 profiles, audience segments, and analytics through a
JWT-secured FastAPI service and a React operations console.

Built against the full specification in [`PROJECT_PLAN.md`](PROJECT_PLAN.md)
for an Adobe Domain 3 (DB + Python + PySpark) portfolio. See
[`docs/PROJECT_DECISIONS.md`](docs/PROJECT_DECISIONS.md) for an honest
account of what is fully implemented, what is reduced in scope, and why.

## What's real here

Every number in this repository is either produced by code you can run, or
marked `TBD (measure)`. In particular:

- **The identity resolution engine is measured against ground truth**, not
  asserted — see [`benchmarks/IDENTITY_EVAL.md`](benchmarks/IDENTITY_EVAL.md)
  (pairwise precision 0.994, recall 0.857 on the `small` profile), including
  a documented bug found and fixed *in the evaluation harness itself* while
  producing that number.
- **The synthetic generator is reproducible and seeded**, with every defect
  injected at a declared rate and recorded in `manifest.json`.
- **All 25 automated tests pass** against a live PostgreSQL 16 instance and
  local-mode PySpark — including the hand-built identity-resolution worked
  examples from the spec (3-hop transitive chain, shared-phone household
  that must *not* merge, generic-email trap, switchboard frequency screen).

## Quickstart

```bash
make venv                 # backend/.venv with all Python dependencies
make generate SIZE=small  # synthetic data -> data/input, data/generated
make migrate              # Alembic schema -> local PostgreSQL
make run-pipeline SIZE=small
make run-api               # FastAPI on :8000 (separate shell)
cd frontend && npm install && npm run dev   # React console on :5173 (separate shell)
```

Or, once Docker is available in your environment:

```bash
cp .env.example .env   # set a real JWT_SECRET_KEY
docker compose up --build
docker compose --profile pipeline run pipeline c360.pipeline.run_pipeline \
    --input-dir /app/data/input --dataset-size small --database-url "$DATABASE_URL"
```

Create a login user:

```bash
cd backend && .venv/bin/python -m c360.cli create-admin \
    --email admin@c360.local --password "<your-password>"
```

## Architecture at a glance

```
generator -> RAW (Parquet, lineage) -> typing/cleaning -> DQ engine
    -> conform -> identity resolution (PySpark) -> aggregation
    -> PostgreSQL (loader) -> FastAPI -> React console
```

Full detail in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and
[`docs/DATA_PIPELINE.md`](docs/DATA_PIPELINE.md).

## Documentation

| Doc | Contents |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Component map, layering, technology choices and why |
| [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md) | Every serving table, column, sensitivity label |
| [`docs/API.md`](docs/API.md) | Endpoint catalogue, auth, error envelope |
| [`docs/SETUP.md`](docs/SETUP.md) | Local dev setup, all commands |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Auth, RBAC matrix, masking, threat model |
| [`docs/TESTING.md`](docs/TESTING.md) | Test suites, how to run them, coverage |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Docker Compose, cloud-readiness mapping |
| [`docs/DATA_PIPELINE.md`](docs/DATA_PIPELINE.md) | Stage-by-stage pipeline detail, Spark mechanics |
| [`docs/PROJECT_DECISIONS.md`](docs/PROJECT_DECISIONS.md) | ADRs, scope reductions, honest gaps |
| [`docs/CHANGELOG.md`](docs/CHANGELOG.md) | What was built, in order |
| [`benchmarks/IDENTITY_EVAL.md`](benchmarks/IDENTITY_EVAL.md) | Identity resolution precision/recall |
| [`benchmarks/RESULTS.md`](benchmarks/RESULTS.md) | Measured pipeline/API timings |

## License

Original work, built for portfolio and educational purposes. No real
customer data is used anywhere in this repository (see `docs/PROJECT_DECISIONS.md`
§ Originality).
