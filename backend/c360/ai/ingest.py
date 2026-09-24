"""Ingest the real Customer360 documentation corpus into `document_chunks`.

Run via `python -m c360.cli ingest-ai-docs` (see c360/cli.py). Idempotent:
truncates and re-inserts every time, so re-running after a doc changes is
safe and produces a consistent chunk count.
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from ..config import Settings
from ..repositories import ai as ai_repo
from .chunking import Chunk, chunk_dq_rules, chunk_markdown, chunk_segments
from .embeddings import get_embedding_provider

MARKDOWN_SOURCES = [
    "docs/DATA_DICTIONARY.md",
    "docs/ARCHITECTURE.md",
    "docs/DATA_PIPELINE.md",
]
DQ_RULES_SOURCE = "config/dq_rules.yaml"
SEGMENTS_SOURCE = "config/segments.yaml"


def build_corpus(repo_root: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for rel_path in MARKDOWN_SOURCES:
        path = repo_root / rel_path
        chunks.extend(chunk_markdown(path.read_text(), rel_path))
    chunks.extend(chunk_dq_rules((repo_root / DQ_RULES_SOURCE).read_text(), DQ_RULES_SOURCE))
    chunks.extend(chunk_segments((repo_root / SEGMENTS_SOURCE).read_text(), SEGMENTS_SOURCE))
    return chunks


def ingest(db: Session, settings: Settings, repo_root: Path) -> int:
    chunks = build_corpus(repo_root)
    embedder = get_embedding_provider(settings.ai_embedding_dim)
    ai_repo.clear_chunks(db)
    for chunk in chunks:
        vector = embedder.embed_query(chunk.content)
        ai_repo.insert_chunk(db, chunk.source, chunk.section, chunk.content, vector, chunk.metadata)
    db.commit()
    return len(chunks)
