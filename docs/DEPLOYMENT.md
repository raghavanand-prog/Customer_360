# Deployment

## Public deployment status (as of this writing)

| Component | Status | URL / detail |
|---|---|---|
| Frontend (React console) | **Live on Vercel** | https://customer360-console.vercel.app/ — verified reachable (HTTP 200 on `/` and on a direct client-side route, `/customers`, confirming the SPA rewrite in `frontend/vercel.json` works) |
| Database (Neon Postgres) | **Provisioned** | `neon-charcoal-village`, free tier, connected via the Vercel Marketplace integration to the `customer360-console` project. Connection string exists only as a Vercel `sensitive`-type env var — never read by, or exposed to, this session |
| Backend (FastAPI project) | **Created, not deployed** | Vercel project `customer360-api` exists (linked to this repo, root directory `backend`), with `JWT_SECRET_KEY` (freshly generated), `CORS_ALLOWED_ORIGINS`, `ENABLE_DOCS=false`, `C360_ENV=prod` already set. It has no deployment yet — see blocker below |

The frontend deployment is real and public, but **without a live backend it
will show error states on every screen that calls the API** (login
included) — that is the honest, correct behaviour per this project's own
rule of never faking API responses, not a bug. `VITE_API_BASE_URL` on the
Vercel project still points at a placeholder
(`https://customer360-api.example.invalid/api/v1`) until the backend below
is actually deployed and reachable.

### The exact remaining step — confirmed blocker

The database exists now, but this session cannot reach it. Vercel's
Marketplace-integration env vars are stored as **`sensitive`** type
specifically so that once written they cannot be read back through the
API or CLI by anyone, including this session — that's the platform working
as designed, not a bug. Two consequences, checked directly against the
live account:

- **The Neon store is connected only to `customer360-console`** (the
  frontend project), not to the new `customer360-api` backend project.
  There is no Vercel API call this session has access to that connects an
  existing storage resource to a second project (Vercel's REST API does
  expose `POST /v1/integrations/installations/{id}/resources/{id}/connections`
  for this, but no MCP tool in this session wraps it, and it still requires
  a Vercel auth token this session doesn't hold).
- **Vercel Sandboxes do not inherit a linked project's env vars** — tested
  directly this session (created a sandbox bound to `customer360-console`;
  `DATABASE_URL` was absent, only 15 base-image variables were present) —
  so there is no way to run `alembic upgrade head` or the pipeline from
  Vercel-side compute either, without the connection string.

Two small compatibility fixes were made and pushed while investigating this
(`backend/c360/config.py`, `backend/alembic/env.py`): Neon hands out a
driver-less `postgresql://` URL, and only `psycopg[binary]` (psycopg3) is
installed here, so both now rewrite that scheme to `postgresql+psycopg://`
before SQLAlchemy opens a connection — otherwise SQLAlchemy would default
to the (uninstalled) psycopg2 dialect and fail outright.

**One manual step unblocks everything else**, and it never requires
sharing the connection string with this session:

1. In the Vercel dashboard, open the `customer360-api` project → **Settings
   → Environment Variables → Connect Store** → select `neon-charcoal-village`
   → connect it for Production + Preview. (Equivalent CLI, from `backend/`
   after `vercel link`: `vercel integration resource connect
   neon-charcoal-village customer360-api`.) This makes `DATABASE_URL` and
   friends available to the backend's own Vercel runtime automatically —
   the same mechanism already working for the frontend project.
2. Tell me once that's done. I'll then deploy `customer360-api` (it will
   have `DATABASE_URL` injected by Vercel at runtime once connected), run
   `alembic upgrade head`, create the admin login, point the frontend's
   `VITE_API_BASE_URL` at the new backend, redeploy the frontend, and run
   the full end-to-end verification — all without ever needing the raw
   connection string typed into this chat.

   The PySpark pipeline is the one piece that genuinely still needs the raw
   connection string somewhere with a working Spark install — that's not
   Vercel's compute (no JVM, execution-time limits, read-only filesystem
   outside `/tmp`) and not this session (same "sensitive" env-var wall
   above). The lowest-friction option: run it yourself, locally, with
   `make generate SIZE=small && python -m c360.pipeline.run_pipeline
   --input-dir ../data/input --dataset-size small --database-url
   "<connection string from the Neon dashboard>"` (from `backend/`) — the
   string never has to leave your machine or be typed into this chat.

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
