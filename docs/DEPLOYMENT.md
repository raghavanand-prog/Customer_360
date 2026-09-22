# Deployment

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
