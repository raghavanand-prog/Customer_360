# Deployment

## Public deployment status (as of this writing)

| Component | Status | URL / detail |
|---|---|---|
| Frontend (React console) | **Live on Vercel** | https://customer360-console.vercel.app/ — rebuilt against the real API URL, verified reachable (HTTP 200) |
| Database (Neon Postgres) | **Provisioned, connected to both projects** | `neon-charcoal-village`, free tier. Connection string exists only as a Vercel `sensitive`-type env var — never read by, or exposed to, this session |
| Backend (FastAPI, Vercel Python runtime) | **Deployed and live** | https://customer360-api.vercel.app — `GET /api/v1/health` returns `200 {"status":"ok"}`, confirming the deployment itself and its env config are correct |
| Database schema / data | **Not yet loaded** | No migrations have been run against Neon, so there are no tables yet — see "One step left" below |

`GET /api/v1/health/detail` (which touches the database) currently returns
`500`, and any endpoint requiring real data will too, until migrations run.
That is the honest, correct behaviour per this project's own rule of never
faking API responses — the backend is genuinely live, the database is
genuinely empty.

### Why migrations run locally, not from an endpoint in the deployment

Two real constraints, checked directly against the live account:

- Vercel's Marketplace-integration env vars are **`sensitive`** type,
  unreadable through the API or CLI by design, by anyone — including this
  session — once written.
- Vercel Sandboxes (ephemeral compute tied to a project) do **not** inherit
  a linked project's env vars either — tested directly (created a sandbox
  bound to a project with a connected Neon store; the variable was absent).

The one place that *does* get `DATABASE_URL` at runtime is the deployed
backend itself, once the store is connected to it (done). It would be
technically possible to add an HTTP endpoint to the deployed app that runs
`alembic upgrade head` on request, authenticated by a bootstrap token —
but that means shipping a permanent, internet-reachable
migration-and-user-creation endpoint in a project whose whole premise is
strict, server-side-enforced security (JWT + RBAC + PII masking, no debug
routes in prod). That is a worse trade than asking you to run one command
locally, so this session does not do that. Migrations and the pipeline both
run from your machine, against the same connection string the Vercel
dashboard already gave you — it never has to be typed into this chat.

A small, necessary compatibility fix was made and pushed for this to work
either way (`backend/c360/config.py`, `backend/alembic/env.py`): Neon hands
out a driver-less `postgresql://` URL, and only `psycopg[binary]` (psycopg3)
is installed here, so both now rewrite that scheme to
`postgresql+psycopg://` before SQLAlchemy opens a connection.

### One step left: load the schema and data

Run this from `backend/`, with `<connection string>` being the one Neon/
Vercel already gave you (Neon dashboard → your project → Connection Details,
or Vercel dashboard → Storage → `neon-charcoal-village`):

```bash
# 1. Apply the schema (34 tables)
MIGRATIONS_DATABASE_URL="<connection string>" .venv/bin/alembic upgrade head

# 2. Generate the reproducible small dataset (if not already generated)
cd .. && make generate SIZE=small && cd backend

# 3. Run the 13-stage pipeline against Neon
.venv/bin/python -m c360.pipeline.run_pipeline \
    --input-dir ../data/input --dataset-size small \
    --database-url "<connection string>"

# 4. Create the login user
.venv/bin/python -m c360.cli create-admin --email <you> --password "<a real password>"
```

Tell me once step 4 is done (just the email, never the password) and I will
verify the schema (`\dt` via `/api/v1/health/detail` or `/api/v1/quality/summary`),
confirm real customer data is being served, and run the remaining
end-to-end checks (login, Customer 360, segments, analytics, DQ, logout)
against the now-populated database.

### What was verified live this session, and what wasn't

This session's only network access to the public URLs is a GET-only fetch
tool routed through Vercel (the sandbox's own network egress is allowlisted
and does not include `*.vercel.app`). That verified, for real, against the
live deployment:

- `GET /api/v1/health` → `200 {"status":"ok"}` (backend deployed, env config valid)
- `GET /api/v1/health/detail` → `500` (reaches Neon, no schema yet — expected)
- `GET /api/v1/customers` with no `Authorization` header → `401 {"code":"unauthenticated","message":"Missing bearer token"}` (RBAC/auth guard is live and enforcing)
- `GET /api/v1/auth/login` → `405 Method Not Allowed` (route exists, correctly POST-only)
- Frontend `/` → `200`, serving the rebuilt bundle with the real `VITE_API_BASE_URL` baked in

Not testable from this session, for lack of a POST/header-capable client or
a real browser: submitting the login form, the JWT/refresh-token cycle,
CORS preflight behaviour, and rejection of a tampered JWT. The relevant code
paths (`CORSMiddleware` bound to `settings.cors_origins_list`, JWT
verification middleware, the 25/25 backend test suite covering auth/RBAC/
PII masking) are unchanged from the already-verified implementation, but
that is a code-review claim, not a live one, and is reported as such rather
than as a live pass.

This is the same sequence `docker-compose.yml` automates locally — Vercel's
Python runtime is an alternative *target* for the same FastAPI app, not a
different app.

## Local (Docker Compose)

`docker-compose.yml` runs: `postgres` (with a role-init script for
`c360_app`/`c360_loader`), `migrate` (one-shot Alembic), `api`, `frontend`
(nginx-served static build), and `pipeline` (on-demand, `--profile
pipeline`). Validated with `docker compose config`; not executed
end-to-end in the sandboxed environment this was built in (no Docker
daemon available there) — every image builds from the same dependency
versions already exercised by the test suite and manual runs recorded in
`benchmarks/RESULTS.md`.

```bash
cp .env.example .env   # set JWT_SECRET_KEY
docker compose up --build
docker compose --profile pipeline run pipeline \
    c360.pipeline.run_pipeline --input-dir /app/data/input \
    --dataset-size small --database-url "$DATABASE_URL"
```

## Cloud readiness (reference mapping, AWS as the worked example)

No cloud dependency exists for local operation — this mapping is a stated
target, not a deployed environment.

| Local component | Managed AWS equivalent |
|---|---|
| PostgreSQL (Docker) | RDS for PostgreSQL (Multi-AZ for prod) |
| Spark pipeline container | EMR Serverless or a scheduled ECS/Fargate task running `spark-submit` |
| Data lake (`data/lake/`) | S3, with the same RAW/STAGING/CURATED prefixes |
| FastAPI container | ECS/Fargate behind an ALB, or App Runner |
| React static build | S3 + CloudFront |
| Pipeline orchestration | The same Typer CLI, invoked by EventBridge Scheduler → ECS RunTask (Airflow/MWAA only if the DAG grows branching/SLA requirements — see ADR-05) |
| Secrets (`JWT_SECRET_KEY`, DB credentials) | AWS Secrets Manager, injected as container env vars |
| Structured logs | CloudWatch Logs (already JSON via `structlog`) |

## What would change for a real multi-instance deployment

- Rate limiting (`slowapi`) needs a shared store (Redis) rather than
  in-process state, once there is more than one API instance — noted but
  not built (`docs/SECURITY.md`).
- The refresh-token family-revocation model already works correctly with
  multiple API instances (it's stateless from the app's perspective — all
  state is in PostgreSQL).
- TLS termination and a WAF sit in front of the ALB; the app itself never
  terminates TLS.
