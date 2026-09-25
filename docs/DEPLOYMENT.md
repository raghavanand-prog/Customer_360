# Deployment

## Public deployment status (as of this writing)

| Component | Status | URL / detail |
|---|---|---|
| Frontend (React console) | **Live on Vercel** | https://customer360-console.vercel.app/ — rebuilt against the real API URL, verified reachable (HTTP 200) |
| Database (Neon Postgres) | **Provisioned, connected to both projects** | `neon-charcoal-village`, free tier. Connection string exists only as a Vercel `sensitive`-type env var — never read by, or exposed to, this session |
| Backend (FastAPI, Vercel Python runtime) | **Deployed and live** | https://customer360-api.vercel.app — `GET /api/v1/health` returns `200 {"status":"ok"}`, confirming the deployment itself and its env config are correct |
| Database schema / data | **Loaded** | All migrations (through `0003_ai_knowledge`) applied to Neon; pipeline data and the AI knowledge base are both present |
| AI knowledge base (`document_chunks`) | **Ingested** | 69 chunks (markdown docs + DQ rules + segment definitions), verified via live `GET /api/v1/ai/status` |
| LLM provider | **Not configured (honest, by design)** | No `ANTHROPIC_API_KEY` set on the Vercel project; `/api/v1/ai/ask` returns an explicit "AI provider not configured" answer, never a fabricated one — verified live |

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

## AI/RAG deployment (Customer360 Intelligence Assistant)

The AI feature's code (`backend/c360/ai/*`, the `/api/v1/ai/*` router,
migration `0003_ai_knowledge`) was already on `main` and auto-deployed to
the live Vercel backend as part of the ordinary git-push deploy — no
separate deploy step exists for it. What this phase actually did, in
order, against the real production Neon database:

1. **Verified the existing deployment state** — `customer360-api` on
   Vercel was `READY`, built from the exact commit containing the AI code;
   Neon env vars (`DATABASE_URL`, etc.) were present as `sensitive`-type
   (unreadable by this session, by design); no `ANTHROPIC_API_KEY` or other
   LLM-provider credential existed on the project.
2. **Applied `alembic upgrade head`** from the user's own machine against
   their real Neon connection string (never typed into this session), which
   created the `document_chunks` and `ai_query_audit` tables.
3. **Ran `python -m c360.cli ingest-ai-docs`**, also from the user's
   machine against the same Neon database. Output: `Ingested 69 document
   chunks into the AI knowledge base.` — matching the corpus size verified
   locally in the phase that built the feature.
4. **Verified live, against the real public API** (`test-verify@example.com`,
   a real `admin`-role account created via the existing `create-admin` CLI
   command against Neon, used only for this verification):
   - `GET /api/v1/ai/status` → `{"configured": false, "provider": "none",
     "knowledge_chunks": 69}` — confirms ingestion landed and the LLM
     provider is genuinely not configured.
   - `POST /api/v1/ai/ask` with a real `customer_id` from `GET
     /api/v1/customers` → correctly routed to `get_customer_profile` and
     `get_customer_segments`, returned real pgvector-retrieved sources
     (e.g. `config/segments.yaml` §"Segment S-06 (Cart Abandoner)",
     score 0.31), and an honest `"AI provider not configured..."` answer
     rather than a fabricated one.
   - `POST /api/v1/ai/ask` with no `customer_id` (general knowledge
     question) → no tools called (correct — nothing customer-scoped was
     asked), real doc-chunk sources returned, same honest not-configured
     answer.

**Not yet done as part of this phase:** testing the "Ask about this
customer" panel through the live frontend UI in a real browser (the
sandbox this session runs in has no direct network route to
`*.vercel.app`; only a GET-only fetch tool and the API calls above were
reachable). The backend behavior behind that UI is verified live per the
above; the UI's rendering of it should be spot-checked manually.

**LLM provider status:** genuinely not configured on the public
deployment. No API key was invented or added. If a real key is added later
(e.g. `ANTHROPIC_API_KEY` as a Vercel env var), `/api/v1/ai/ask` will use
it automatically — the provider abstraction is already wired — but that
path remains unverified against a live account until it happens.

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
