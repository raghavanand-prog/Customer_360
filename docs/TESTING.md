# Testing

## Philosophy

Every test in this suite runs against real infrastructure — a live local
PostgreSQL 16 instance and local-mode PySpark — not mocks of either. This
was a deliberate choice: the components most worth proving (the DQ
engine's classification invariant, the identity resolver's worked
examples, the API's actual HTTP behaviour) are exactly the components
where a mock would hide the bug that matters.

## Suites (all in `backend/tests/`)

| File | What it proves | Runtime |
|---|---|---|
| `test_generator.py` | Byte-identical reproducibility across two runs with the same seed; manifest/dataset consistency; zero realised defects under `--defect-profile none`; seeded defects are actually observable in the raw output | ~2 min (spawns the generator as a subprocess 4×) |
| `test_dq_engine.py` | Record-conservation invariant (`accepted+warned+quarantined+rejected == ingested`); ≥30 rules across all 6 dimensions; zero false positives on defect-free data | ~30 s |
| `test_identity_resolution.py` | All of §10.8's hand-built worked examples: the 3-hop transitive chain, the shared-phone household that must **not** merge (attribute-conflict guard), the generic-email screen, the switchboard frequency screen, the no-identifier singleton, and canonical-ID stability across two runs on unchanged input | ~50 s |
| `test_api.py` | Live HTTP behaviour via FastAPI's `TestClient`: 401 without a token, login success/failure, full Customer 360 profile response shape, 404 on an unknown customer, segment listing | <1 s (skipped automatically without `DATABASE_URL`/`JWT_SECRET_KEY`) |

25 tests total, all passing as of the last commit in this repository's
history.

## Running

```bash
cd backend
DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/c360" \
JWT_SECRET_KEY="test-secret" \
    .venv/bin/python -m pytest tests/ -q
```

`test_api.py` additionally requires a pipeline run to have loaded at least
one customer and one admin user (`c360.cli create-admin`) — see
`docs/SETUP.md`.

## What the coverage targets in `PROJECT_PLAN.md` §19.6 ask for, and what exists

The plan specifies coverage percentages per layer (rule engine, identity,
API) and a broader set of suites (Spark unit tests separate from
integration, dedicated DQ rule-type tests, E2E browser flows via a test
runner, security/injection tests as a dedicated suite, frontend component
tests). A formal coverage report (`pytest-cov`) was not generated in this
session, and the four suites above are integration-level rather than
split into the full unit/integration/E2E/security taxonomy the plan lays
out. The Playwright smoke test used during development (login → overview →
customer search → profile, verifying no console errors) exercised the
critical E2E path described in §19.5 but was not committed as a repeatable
CI job — see `docs/PROJECT_DECISIONS.md` for the honest gap list.

## Dual-backend segment equivalence (T-17)

Not implemented: segments in this build have a SQL backend only
(`c360/segments/compiler.py`), used for both preview and full recompute.
The Spark-backend compiler described in §14.4, and the equivalence test
between the two, were scoped out for time — see `PROJECT_DECISIONS.md`
ADR-14.
