# Deployment

## Public deployment status (as of this writing)

| Component | Status | URL / detail |
|---|---|---|
| Frontend (React console) | **Live on Vercel** | https://customer360-console.vercel.app/ — verified reachable (HTTP 200 on `/` and on a direct client-side route, `/customers`, confirming the SPA rewrite in `frontend/vercel.json` works) |
| Backend (FastAPI) | **Not deployed** | Blocked on a persistent, internet-reachable PostgreSQL instance. See "The exact remaining step" below |
| Database | **Not provisioned** | No hosted Postgres was created — see below |

The frontend deployment is real and public, but **without a live backend it
will show error states on every screen that calls the API** (login
included) — that is the honest, correct behaviour per this project's own
rule of never faking API responses, not a bug. `VITE_API_BASE_URL` on the
Vercel project currently points at a placeholder
(`https://customer360-api.example.invalid/api/v1`) until a real backend
exists.

### The exact remaining step

Provisioning a production PostgreSQL database requires an action in a
dashboard (accepting a marketplace integration's terms, or creating an
account with a database host) that cannot be completed via API calls
alone, and involves a billing/ToS decision that should be made by the
project owner, not an agent. Repository-side preparation is complete:
`backend/vercel.json` + `backend/api/index.py` are ready for Vercel's
Python runtime to serve the existing FastAPI app with **no further code
changes**. The remaining steps, once a database exists:

1. Provision Postgres — e.g. in the Vercel dashboard: **Storage → Marketplace Database Providers → Neon** (or Supabase), or any external host (Railway, Render, Supabase, RDS). Copy the connection string.
2. Run migrations against it: `MIGRATIONS_DATABASE_URL="<that connection string>" alembic upgrade head` (from `backend/`).
3. Run the pipeline once against it so the console has real data to show: `python -m c360.pipeline.run_pipeline --input-dir ../data/input --dataset-size small --database-url "<that connection string>"` (after `make generate SIZE=small`).
4. Create a login user: `python -m c360.cli create-admin --email <you> --password <password>`.
5. Create a Vercel project for `backend/` (root directory `backend`), and set its environment variables: `DATABASE_URL` (the connection string, `postgresql+psycopg://…`), `JWT_SECRET_KEY` (a long random value), `CORS_ALLOWED_ORIGINS=https://customer360-console.vercel.app`, `ENABLE_DOCS=false`, `C360_ENV=prod`.
6. Update the frontend's `VITE_API_BASE_URL` env var to the new backend's URL + `/api/v1` and redeploy the frontend.

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
