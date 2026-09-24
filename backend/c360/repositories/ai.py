"""Repository for the RAG knowledge base and AI query audit log.

Follows this codebase's existing convention (see repositories/customers.py):
raw parametrized `sqlalchemy.text()` queries, no ORM models.
"""
from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..ai.embeddings import to_pgvector_literal


def clear_chunks(db: Session) -> None:
    db.execute(text("TRUNCATE document_chunks RESTART IDENTITY"))
    db.commit()


def insert_chunk(db: Session, source: str, section: str, content: str, embedding: list[float], metadata: dict) -> int:
    row = db.execute(
        text(
            "INSERT INTO document_chunks (source, section, content, embedding, metadata) "
            "VALUES (:source, :section, :content, CAST(:embedding AS vector), CAST(:metadata AS jsonb)) "
            "RETURNING chunk_id"
        ),
        {
            "source": source,
            "section": section,
            "content": content,
            "embedding": to_pgvector_literal(embedding),
            "metadata": json.dumps(metadata),
        },
    ).first()
    return row[0]


def count_chunks(db: Session) -> int:
    return db.execute(text("SELECT count(*) FROM document_chunks")).scalar_one()


def search_similar_chunks(db: Session, query_embedding: list[float], top_k: int) -> list[dict]:
    """Cosine-similarity retrieval via pgvector's `<=>` (cosine distance) operator.

    `score` is `1 - distance`, so higher is more similar (range roughly -1..1).
    """
    rows = db.execute(
        text(
            "SELECT source, section, content, metadata, "
            "1 - (embedding <=> CAST(:qvec AS vector)) AS score "
            "FROM document_chunks "
            "ORDER BY embedding <=> CAST(:qvec AS vector) "
            "LIMIT :k"
        ),
        {"qvec": to_pgvector_literal(query_embedding), "k": top_k},
    ).mappings().all()
    return [dict(r) for r in rows]


def write_ai_audit(
    db: Session, user_id: int | None, actor_email: str | None, customer_id: str | None,
    question: str, tools_called: list[str], sources: list[dict], provider: str,
    model: str | None, configured: bool, request_id: str | None,
) -> None:
    db.execute(
        text(
            "INSERT INTO ai_query_audit "
            "(user_id, actor_email, customer_id, question, tools_called, sources, provider, model, configured, request_id) "
            "VALUES (:user_id, :actor_email, :customer_id, :question, CAST(:tools_called AS jsonb), "
            "CAST(:sources AS jsonb), :provider, :model, :configured, :request_id)"
        ),
        {
            "user_id": user_id,
            "actor_email": actor_email,
            "customer_id": customer_id,
            "question": question,
            "tools_called": json.dumps(tools_called),
            "sources": json.dumps(sources),
            "provider": provider,
            "model": model,
            "configured": configured,
            "request_id": request_id,
        },
    )
    db.commit()
