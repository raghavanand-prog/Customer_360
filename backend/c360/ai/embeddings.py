"""Embedding provider abstraction (§9 of the Adobe-JD AI phase).

Only one implementation is actually exercised in this environment: the
deterministic, local, hashed lexical embedding below. No external embedding
provider is configured or paid for anywhere in this project, so no such
provider is claimed to work -- only that the abstraction exists for one to
be plugged in later.

Honesty note on what `DeterministicLocalEmbedding` actually is: it is a
feature-hashed bag-of-words vector (a classic, well-understood technique --
the "hashing trick"), not a trained semantic embedding model. Cosine
similarity between two such vectors reflects *lexical* overlap (shared
words/stems), not semantic meaning. It will find "identity resolution" text
when asked about "identity resolution", but it will not know that "churn"
and "attrition" are related concepts the way a model like OpenAI's
text-embedding-3 or Voyage would. This is documented, not hidden, in
docs/AI_EVALUATION.md.
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class EmbeddingProvider(Protocol):
    """Interface every embedding provider implements."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, text: str) -> list[float]:
        ...


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class DeterministicLocalEmbedding:
    """Feature-hashed bag-of-words embedding. No network calls, no API key.

    Deterministic: the same text always produces the same vector, which is
    what makes this usable as a test fixture as well as the only provider
    actually exercised in production today.
    """

    provider_name = "local-hashed-lexical"

    def __init__(self, dim: int = 256):
        self.dim = dim

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in _tokenize(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[index] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            return vec
        return [v / norm for v in vec]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]


def get_embedding_provider(dim: int) -> EmbeddingProvider:
    # Only one provider exists today. This function is the seam a real
    # provider (behind an env-configured API key) would be added at,
    # without any caller needing to change.
    return DeterministicLocalEmbedding(dim=dim)


def to_pgvector_literal(vector: list[float]) -> str:
    """Render a Python float list as the text form pgvector's input parser expects."""
    return "[" + ",".join(f"{v:.8f}" for v in vector) + "]"
