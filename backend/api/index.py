"""Vercel Python serverless entrypoint for the FastAPI app.

Only used by the Vercel deployment path (backend/vercel.json). The
primary, verified deployment path is the Docker image
(backend/Dockerfile.api) run via `uvicorn c360.main:app`, per
docs/DEPLOYMENT.md -- this file exists so that once a reachable
PostgreSQL instance and JWT_SECRET_KEY are configured as Vercel
environment variables, the API can be deployed with no further code
changes. It has not been exercised against a live database from this
environment; see docs/PROJECT_DECISIONS.md.
"""
from c360.main import app  # noqa: F401  (Vercel's Python runtime serves the ASGI `app`)
