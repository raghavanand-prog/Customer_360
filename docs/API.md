# API

Base path `/api/v1`. Interactive docs at `/docs` when `ENABLE_DOCS=true`
(default outside `prod`). Every endpoint below is implemented and covered
by `backend/tests/test_api.py` where noted.

## Auth

| Method | Route | Notes |
|---|---|---|
| POST | `/auth/login` | `{email, password}` → access + refresh tokens. Argon2id verify. Tested. |
| POST | `/auth/refresh` | Reuse detection: a revoked/unknown `jti` revokes the whole token family. |
| POST | `/auth/logout` | Revokes the given refresh token. |
| GET | `/auth/me` | Current user + roles. Tested. |

## Customers

| Method | Route | Min role | Notes |
|---|---|---|---|
| GET | `/customers` | viewer | Search by `q` (name/email/phone/exact ID), `churn_risk_band`; offset-paginated. Tested. |
| GET | `/customers/{id}` | viewer | Attribute block, PII-masked for `viewer`/`analyst`. |
| GET | `/customers/{id}/profile` | viewer | Full Customer 360: identity, profile, metrics, recent orders, segments, quality flags. Tested. |
| GET | `/customers/{id}/metrics` | viewer | `customer_metrics` row. |
| GET | `/customers/{id}/identities` | analyst | Linked source records. |
| GET | `/customers/{id}/orders` | viewer | Recent orders, newest first. |
| GET | `/customers/{id}/timeline` | viewer | Union of orders/events/tickets/marketing, newest first. |
| GET | `/customers/{id}/segments` | viewer | Current segment memberships. |
| GET | `/customers/{id}/quality` | analyst | Quarantined records referencing this customer. |

A canonical ID that was merged into a survivor resolves transparently via
`identity_crosswalk`; a split ID returns `409 identity_ambiguous` (§10.7)
rather than silently picking a successor.

## Segments

| Method | Route | Min role |
|---|---|---|
| GET | `/segments` | viewer |
| GET | `/segments/{id}` | viewer — definition, rule AST, version history |
| GET | `/segments/{id}/members` | viewer — paginated members |

Recompute is driven by `c360/segments/evaluator.py` (called from the
pipeline or standalone), not by a dedicated `POST /segments/{id}/recompute`
endpoint in this implementation — see `PROJECT_DECISIONS.md`.

## Analytics

`GET /analytics/summary`, `/revenue`, `/top-customers`,
`/churn-distribution`, `/rfm-distribution`, `/repeat-rate` — all viewer+,
all backed by parameterised SQL in `c360/repositories/analytics.py`.

## Data quality

`GET /quality/summary`, `/datasets`, `/datasets/{dataset}`,
`/datasets/{dataset}/trend`, `/records` — dataset-level scores and
per-rule drill-down from the most recent successful pipeline run.

## Pipeline

`GET /pipeline/runs`, `/runs/{id}`, `/runs/{id}/stages`, `/latest` — read
access to `pipeline_runs`/`pipeline_stage_runs`. Triggering a run from the
API (`POST /pipeline/runs`) was not implemented — runs are triggered via
the CLI (`c360.pipeline.run_pipeline`); see `PROJECT_DECISIONS.md`.

## Health

`GET /health` — liveness only, no dependency checks (responds even with
the database down). `GET /health/detail` — DB connectivity, last
successful run, key row counts.

## Error envelope

Every non-2xx response:

```json
{"error": {"code": "not_found", "message": "...", "request_id": "...", "details": {}}}
```

| Situation | Status | `code` |
|---|---|---|
| Validation failure | 422 | `validation_error` |
| Missing/invalid token | 401 | `unauthenticated` |
| Wrong/expired token | 401 | `token_expired` |
| Refresh reuse detected | 401 | `token_reuse_detected` |
| Insufficient role | 403 | `insufficient_role` |
| Not found | 404 | `not_found` |
| Split canonical ID | 409 | `identity_ambiguous` |
| Unhandled | 500 | `internal_error` |

## What's in `PROJECT_PLAN.md` §16.6 but not implemented here

Admin user management (`/admin/*`), audience export
(`/segments/{id}/export`), segment preview/create/update
(`POST/PUT /segments`), identity review-queue endpoints, and the
`/metrics` Prometheus endpoint were designed but not built in this
session — full accounting in `docs/PROJECT_DECISIONS.md`.
