"""API integration tests (T-18ish): run against a live Postgres instance
with the schema migrated and at least one pipeline run loaded. Skipped
automatically if DATABASE_URL is not set (e.g. in an offline unit-test-only
environment) -- see docs/TESTING.md.
"""
import os

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skipif(
    "DATABASE_URL" not in os.environ or "JWT_SECRET_KEY" not in os.environ,
    reason="requires a live PostgreSQL instance (DATABASE_URL) and JWT_SECRET_KEY",
)


@pytest.fixture(scope="module")
def client():
    from c360.main import create_app
    return TestClient(create_app())


def test_health_no_auth_required(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_unauthenticated_request_is_401(client):
    resp = client.get("/api/v1/customers")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthenticated"


def test_login_wrong_password_is_401(client):
    resp = client.post("/api/v1/auth/login", json={"email": "admin@c360.local", "password": "wrong"})
    assert resp.status_code == 401


@pytest.fixture(scope="module")
def token(client):
    resp = client.post("/api/v1/auth/login", json={"email": "admin@c360.local", "password": "Admin123!Pass"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def test_me_returns_roles(client, token):
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "admin" in resp.json()["roles"]


def test_analytics_summary_shape(client, token):
    resp = client.get("/api/v1/analytics/summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert "total_customers" in body and "total_revenue" in body


def test_customer_search_and_profile(client, token):
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/v1/customers?limit=1", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    cid = items[0]["canonical_customer_id"]

    profile_resp = client.get(f"/api/v1/customers/{cid}/profile", headers=headers)
    assert profile_resp.status_code == 200
    profile = profile_resp.json()
    assert profile["identity"]["canonical_customer_id"] == cid
    assert "metrics" in profile and "segments" in profile


def test_unknown_customer_is_404(client, token):
    resp = client.get("/api/v1/customers/CXdoesnotexist000/profile", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_segments_list(client, token):
    resp = client.get("/api/v1/segments", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 8


def test_quality_summary(client, token):
    resp = client.get("/api/v1/quality/summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()["datasets"]) > 0
