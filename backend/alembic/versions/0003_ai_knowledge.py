"""AI knowledge base for the Customer360 Intelligence Assistant (RAG).

Adds the `pgvector` extension and a single `document_chunks` table storing
chunked project documentation with embeddings, retrieved by cosine
similarity for the grounded assistant (see `c360/ai/`). Deliberately one
table in the existing Postgres instance rather than a separate vector
database -- see ADR in docs/PROJECT_DECISIONS.md ("Why pgvector, not a
separate vector database").

The embedding dimension (256) matches the deterministic local hashed
embedding in `c360/ai/embeddings.py`, the only embedding path exercised in
this environment (no external embedding provider is configured or paid
for). If a real embedding model is plugged in later with a different
dimension, this column must be migrated (`ALTER COLUMN embedding TYPE
vector(<new_dim>)`), not silently reused.

Revision ID: 0003_ai_knowledge
Revises: 0002_grants
Create Date: 2026-09-24
"""
from __future__ import annotations

from alembic import op

revision = "0003_ai_knowledge"
down_revision = "0002_grants"
branch_labels = None
depends_on = None

EMBEDDING_DIM = 256

UPGRADE_DDL = f"""
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE document_chunks (
    chunk_id        BIGSERIAL PRIMARY KEY,
    source          TEXT NOT NULL,
    section         TEXT NOT NULL,
    content         TEXT NOT NULL,
    embedding       vector({EMBEDDING_DIM}) NOT NULL,
    metadata        JSONB NOT NULL DEFAULT '{{}}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_document_chunks_source ON document_chunks (source);

-- Deliberately NO approximate-nearest-neighbour index (e.g. ivfflat) here.
-- This corpus is ~70-150 chunks; an ivfflat index needs roughly
-- rows >> lists to partition sensibly, and was verified during development
-- to silently return ZERO results at this scale with pgvector's default
-- `probes = 1` (lists=100 on 69 rows put most rows in lists never probed).
-- A plain sequential scan over a few hundred rows is both exact and fast
-- enough that an approximate index buys nothing here -- see the ADR in
-- docs/PROJECT_DECISIONS.md and the honest note in docs/AI_EVALUATION.md.
-- Add an ivfflat/hnsw index only once the corpus is large enough (low
-- thousands+) to actually benefit, and re-verify recall after adding it.

CREATE TABLE ai_query_audit (
    audit_id        BIGSERIAL PRIMARY KEY,
    user_id         BIGINT REFERENCES users(user_id) ON DELETE SET NULL,
    actor_email     TEXT,
    customer_id     TEXT,
    question        TEXT NOT NULL,
    tools_called    JSONB NOT NULL DEFAULT '[]'::jsonb,
    sources         JSONB NOT NULL DEFAULT '[]'::jsonb,
    provider        TEXT NOT NULL,
    model           TEXT,
    configured      BOOLEAN NOT NULL,
    request_id      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_ai_query_audit_user ON ai_query_audit (user_id);
CREATE INDEX ix_ai_query_audit_customer ON ai_query_audit (customer_id);
"""

DOWNGRADE_DDL = """
DROP TABLE IF EXISTS ai_query_audit;
DROP TABLE IF EXISTS document_chunks;
"""


def upgrade() -> None:
    op.execute(UPGRADE_DDL)


def downgrade() -> None:
    op.execute(DOWNGRADE_DDL)
