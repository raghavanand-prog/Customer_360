"""Admin CLI: user bootstrap (`python -m c360.cli create-user ...`)."""
from __future__ import annotations

from pathlib import Path

import typer
from sqlalchemy.orm import Session

from .ai.ingest import ingest as ingest_ai_docs
from .config import get_settings
from .db import get_sessionmaker
from .repositories.users import create_user, get_user_by_email
from .security.hashing import hash_password
from .segments.evaluator import evaluate_all

app = typer.Typer(add_completion=False)


@app.command()
def create_admin(email: str = typer.Option(...), password: str = typer.Option(...),
                  full_name: str = typer.Option("Administrator")) -> None:
    db: Session = get_sessionmaker()()
    try:
        if get_user_by_email(db, email):
            typer.echo(f"User {email} already exists.")
            return
        user_id = create_user(db, email, hash_password(password), full_name, ["admin"])
        typer.echo(f"Created admin user {email} (id={user_id})")
    finally:
        db.close()


@app.command()
def create_user_cmd(email: str = typer.Option(...), password: str = typer.Option(...),
                     full_name: str = typer.Option(""), role: str = typer.Option("viewer")) -> None:
    db: Session = get_sessionmaker()()
    try:
        if get_user_by_email(db, email):
            typer.echo(f"User {email} already exists.")
            return
        user_id = create_user(db, email, hash_password(password), full_name, [role])
        typer.echo(f"Created user {email} with role {role} (id={user_id})")
    finally:
        db.close()


@app.command(name="evaluate-segments")
def evaluate_segments_cmd(
    database_url: str = typer.Option(..., envvar="DATABASE_URL", help="Plain postgresql:// URL (raw psycopg, not SQLAlchemy)"),
) -> None:
    """Recompute all segment memberships from config/segments.yaml (§14.5).

    Previously only ever invoked ad hoc / manually -- not wired to
    run_pipeline, the CLI, or the Makefile, despite being fully implemented
    in c360/segments/evaluator.py. Wired up here so segment membership is
    reproducible from a clean database rather than relying on leftover
    state in a long-lived dev database.
    """
    import psycopg

    config_path = Path(__file__).resolve().parents[2] / "config" / "segments.yaml"
    conn = psycopg.connect(database_url, autocommit=False)
    try:
        results = evaluate_all(conn, config_path)
        for r in results:
            typer.echo(f"{r['segment_id']}: {r['member_count']} members ({r['entered']} entered, {r['exited']} exited)")
    finally:
        conn.close()


@app.command(name="ingest-ai-docs")
def ingest_ai_docs_cmd() -> None:
    """Chunk + embed the real project docs into `document_chunks` for the RAG assistant."""
    db: Session = get_sessionmaker()()
    try:
        settings = get_settings()
        repo_root = Path(__file__).resolve().parents[2]
        count = ingest_ai_docs(db, settings, repo_root)
        typer.echo(f"Ingested {count} document chunks into the AI knowledge base.")
    finally:
        db.close()


if __name__ == "__main__":
    app()
