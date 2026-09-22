"""Least-privilege grants for c360_app / c360_loader (§6.2, §18.8).

Guarded so this migration is a no-op (not a failure) when those roles do
not exist yet -- e.g. a local dev database created before the Compose
Postgres init script ran.

Revision ID: 0002_grants
Revises: 0001_initial_schema
Create Date: 2026-09-22
"""
from __future__ import annotations

from alembic import op

revision = "0002_grants"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None

DDL = """
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'c360_app') THEN
        GRANT USAGE ON SCHEMA public TO c360_app;
        GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO c360_app;
        GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO c360_app;
        REVOKE DELETE ON audit_logs FROM c360_app;
        REVOKE ALL ON audit_logs FROM c360_app;
        GRANT SELECT, INSERT ON audit_logs TO c360_app;
    END IF;
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'c360_loader') THEN
        GRANT USAGE ON SCHEMA public TO c360_loader;
        GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO c360_loader;
        GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO c360_loader;
        REVOKE ALL ON audit_logs FROM c360_loader;
    END IF;
END
$$;
"""


def upgrade() -> None:
    op.execute(DDL)


def downgrade() -> None:
    pass
