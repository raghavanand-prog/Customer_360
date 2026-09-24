.PHONY: venv generate migrate run-pipeline evaluate-segments ingest-ai-docs run-api run-frontend test demo up down

VENV := backend/.venv
PY := $(VENV)/bin/python
SIZE ?= small
SEED ?= 20260922
DATABASE_URL ?= postgresql://postgres:postgres@localhost:5432/c360

venv:
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -q --upgrade pip
	$(VENV)/bin/pip install -q -r backend/requirements-dev.txt

generate:
	cd backend && ../$(PY) -m c360.generator.main --seed $(SEED) --size $(SIZE) --out-dir ../data --defect-profile default

migrate:
	cd backend && MIGRATIONS_DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/c360" ../$(VENV)/bin/alembic upgrade head

run-pipeline:
	cd backend && DATABASE_URL="$(DATABASE_URL)" ../$(PY) -m c360.pipeline.run_pipeline --input-dir ../data/input --dataset-size $(SIZE) --database-url "$(DATABASE_URL)"

evaluate-segments:
	cd backend && ../$(PY) -m c360.cli evaluate-segments --database-url "$(DATABASE_URL)"

ingest-ai-docs:
	cd backend && DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/c360" JWT_SECRET_KEY=dev-secret ../$(PY) -m c360.cli ingest-ai-docs

run-api:
	cd backend && DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/c360" JWT_SECRET_KEY=dev-secret C360_ENV=local ../$(VENV)/bin/uvicorn c360.main:app --reload

run-frontend:
	cd frontend && npm run dev

test:
	cd backend && ../$(PY) -m pytest tests/ -q

demo: generate migrate run-pipeline evaluate-segments ingest-ai-docs
	@echo "Demo data generated and loaded. Run 'make run-api' and 'make run-frontend' in separate shells."

up:
	docker compose up --build

down:
	docker compose down -v
