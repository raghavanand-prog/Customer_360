# Setup

## Prerequisites

- Python 3.11
- Java 17+ (for local-mode PySpark)
- PostgreSQL 16 (local install or Docker)
- Node 20+ / npm

## Backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt   # includes PySpark + pytest
```

Environment (see `c360/config.py` for the full list):

```bash
export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/c360"
export JWT_SECRET_KEY="a long random value -- the app refuses to start without one"
export C360_ENV=local
```

## Database

```bash
createdb c360   # or: docker run -e POSTGRES_DB=c360 ... postgres:16
cd backend
MIGRATIONS_DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/c360" \
    .venv/bin/alembic upgrade head
```

## Generate data and run the pipeline

```bash
cd backend
.venv/bin/python -m c360.generator.main --seed 20260922 --size small \
    --out-dir ../data --defect-profile default

DATABASE_URL="postgresql://postgres:postgres@localhost:5432/c360" \
    .venv/bin/python -m c360.pipeline.run_pipeline \
    --input-dir ../data/input --dataset-size small \
    --database-url "$DATABASE_URL"

# Segments are evaluated against the loaded customer_metrics separately:
.venv/bin/python -c "
import psycopg
from c360.segments.evaluator import evaluate_all
conn = psycopg.connect('postgresql://postgres:postgres@localhost:5432/c360')
print(evaluate_all(conn, '../config/segments.yaml', run_id=1))
"
```

## Create a login user

```bash
.venv/bin/python -m c360.cli create-admin --email admin@c360.local --password "<password>"
```

## Run the API

```bash
.venv/bin/uvicorn c360.main:app --reload
# -> http://localhost:8000/docs
```

## Run the frontend

```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_BASE_URL, defaults to http://localhost:8000/api/v1
npm run dev
# -> http://localhost:5173
```

## Run the tests

```bash
cd backend
DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/c360" \
JWT_SECRET_KEY="test-secret" \
    .venv/bin/python -m pytest tests/ -q
```

Generator and DQ-engine tests spin up local-mode Spark and take a few
minutes in total; API tests are skipped automatically if `DATABASE_URL`/
`JWT_SECRET_KEY` are not set (see `docs/TESTING.md`).

## Docker Compose

```bash
cp .env.example .env   # set JWT_SECRET_KEY
docker compose up --build
```

This was validated with `docker compose config` but not executed
end-to-end in the environment this project was built in (no Docker daemon
available there) — see `docs/PROJECT_DECISIONS.md`.
