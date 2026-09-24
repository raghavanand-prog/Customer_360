"""Tests for the Customer360 Intelligence Assistant (RAG/agent/tools).

Two groups, mirroring test_api.py's convention:
- Pure unit tests (embeddings, chunking, tool-routing policy) that need no
  database and always run.
- Integration tests against a live Postgres instance with the AI knowledge
  base ingested, gated by the same skipif as test_api.py.
"""
from __future__ import annotations

import os

import pytest

from c360.ai.chunking import chunk_dq_rules, chunk_markdown, chunk_segments
from c360.ai.embeddings import DeterministicLocalEmbedding, to_pgvector_literal
from c360.ai.agent import route_question


# --- Pure unit tests: embeddings -------------------------------------------

def test_embedding_is_deterministic():
    embedder = DeterministicLocalEmbedding(dim=64)
    v1 = embedder.embed_query("high value customer segment")
    v2 = embedder.embed_query("high value customer segment")
    assert v1 == v2


def test_embedding_dimension_matches_config():
    embedder = DeterministicLocalEmbedding(dim=256)
    v = embedder.embed_query("anything")
    assert len(v) == 256


def test_embedding_is_l2_normalised():
    embedder = DeterministicLocalEmbedding(dim=64)
    v = embedder.embed_query("some reasonably long piece of text to embed")
    norm = sum(x * x for x in v) ** 0.5
    assert abs(norm - 1.0) < 1e-6


def test_similar_text_more_similar_than_unrelated_text():
    embedder = DeterministicLocalEmbedding(dim=256)

    def cosine(a, b):
        return sum(x * y for x, y in zip(a, b))

    base = embedder.embed_query("customer segment high value spend threshold")
    similar = embedder.embed_query("segment high value customer spend rules")
    unrelated = embedder.embed_query("zebra airplane telescope umbrella")
    assert cosine(base, similar) > cosine(base, unrelated)


def test_pgvector_literal_format():
    literal = to_pgvector_literal([1.0, -0.5, 0.0])
    assert literal.startswith("[") and literal.endswith("]")
    assert literal.count(",") == 2


# --- Pure unit tests: chunking ----------------------------------------------

def test_chunk_markdown_splits_on_headings():
    text = "## First\ncontent one\n\n## Second\ncontent two\n"
    chunks = chunk_markdown(text, "test.md")
    assert [c.section for c in chunks] == ["First", "Second"]
    assert chunks[0].content == "content one"


def test_chunk_dq_rules_produces_one_chunk_per_rule():
    yaml_text = """
version: 1
datasets:
  customers_crm:
    rules:
      - id: Q-01
        name: email_present
        dimension: completeness
        type: not_null
        column: email
        severity: warn
      - id: Q-02
        name: phone_present
        dimension: completeness
        type: not_null
        column: phone
        severity: info
"""
    chunks = chunk_dq_rules(yaml_text, "config/dq_rules.yaml")
    assert len(chunks) == 2
    assert chunks[0].metadata["rule_id"] == "Q-01"
    assert "email" in chunks[0].content


def test_chunk_segments_produces_one_chunk_per_segment():
    yaml_text = """
segments:
  - id: S-01
    name: High Value
    description: Big spenders.
    null_handling: exclude
    rule_ast: {op: ">=", field: total_spend, value: {param: threshold}}
    thresholds: {threshold: 100000}
"""
    chunks = chunk_segments(yaml_text, "config/segments.yaml")
    assert len(chunks) == 1
    assert chunks[0].metadata["segment_id"] == "S-01"
    assert "High Value" in chunks[0].content


# --- Pure unit tests: deterministic tool-routing policy ---------------------

def test_routing_returns_nothing_without_customer_id():
    assert route_question("why is this customer high value", has_customer_id=False) == []


def test_routing_always_includes_profile_when_customer_id_present():
    tools = route_question("hello", has_customer_id=True)
    assert tools == ["get_customer_profile"]


def test_routing_maps_segment_keywords():
    tools = route_question("why is this customer in the high value segment", has_customer_id=True)
    assert "get_customer_segments" in tools


def test_routing_maps_identity_keywords():
    tools = route_question("why are these identities linked to the same customer", has_customer_id=True)
    assert "get_customer_identities" in tools


def test_routing_maps_quality_keywords():
    tools = route_question("what data quality issues affect this customer", has_customer_id=True)
    assert "get_customer_quality" in tools


def test_routing_never_exceeds_hard_cap():
    tools = route_question(
        "segment identity quality timeline recent activity rfm metric spend clv churn engagement",
        has_customer_id=True,
    )
    assert len(tools) <= 6


# --- Integration tests: live DB, real JWT, same pattern as test_api.py -----

pytestmark_integration = pytest.mark.skipif(
    "DATABASE_URL" not in os.environ or "JWT_SECRET_KEY" not in os.environ,
    reason="requires a live PostgreSQL instance (DATABASE_URL) and JWT_SECRET_KEY",
)


@pytestmark_integration
class TestAiEndpointIntegration:
    @pytest.fixture(scope="class")
    def client(self):
        from fastapi.testclient import TestClient
        from c360.main import create_app
        return TestClient(create_app())

    @pytest.fixture(scope="class")
    def token(self, client):
        resp = client.post("/api/v1/auth/login", json={"email": "admin@c360.local", "password": "Admin123!Pass"})
        assert resp.status_code == 200, resp.text
        return resp.json()["access_token"]

    def test_ask_requires_auth(self, client):
        resp = client.post("/api/v1/ai/ask", json={"question": "hi"})
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "unauthenticated"

    def test_ask_rejects_invalid_token(self, client):
        resp = client.post(
            "/api/v1/ai/ask", json={"question": "hi"},
            headers={"Authorization": "Bearer not-a-real-token"},
        )
        assert resp.status_code == 401

    def test_status_reports_ingested_chunks(self, client, token):
        resp = client.get("/api/v1/ai/status", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        body = resp.json()
        assert "configured" in body and "knowledge_chunks" in body
        assert body["knowledge_chunks"] > 0, "run `python -m c360.cli ingest-ai-docs` before this test"

    def test_ask_without_customer_returns_shape(self, client, token):
        resp = client.post(
            "/api/v1/ai/ask", json={"question": "What data-quality rules exist for email addresses?"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        for key in ("answer", "tools_called", "tool_denied", "sources", "provider", "configured"):
            assert key in body
        assert isinstance(body["sources"], list)

    def test_ask_with_real_customer_calls_profile_tool(self, client, token):
        headers = {"Authorization": f"Bearer {token}"}
        customers = client.get("/api/v1/customers?limit=1", headers=headers).json()["items"]
        cid = customers[0]["canonical_customer_id"]
        resp = client.post(
            "/api/v1/ai/ask",
            json={"question": "Summarise this customer's recent behaviour.", "customer_id": cid},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "get_customer_profile" in body["tools_called"]

    def test_ask_with_unknown_customer_does_not_error(self, client, token):
        resp = client.post(
            "/api/v1/ai/ask",
            json={"question": "test", "customer_id": "NOT-A-REAL-CUSTOMER-ID"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    def test_ask_rejects_oversized_question(self, client, token):
        resp = client.post(
            "/api/v1/ai/ask", json={"question": "x" * 5000},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422
