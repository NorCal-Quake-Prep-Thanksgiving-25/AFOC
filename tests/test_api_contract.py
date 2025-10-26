from __future__ import annotations

import hashlib  # Security: tests mirror production hashing to validate credential paths.
import json

import pytest

fastapi = pytest.importorskip("fastapi")
testclient = pytest.importorskip("fastapi.testclient")

from afoc.api import build_api
from afoc.core import ComposableIntelligenceCore


@pytest.fixture()
def api_client(monkeypatch: pytest.MonkeyPatch) -> testclient.TestClient:
    monkeypatch.setenv("AFOC_APP_SECRET", "test-secret")
    monkeypatch.setenv("AFOC_AUDIT_HMAC_SECRET", "audit-secret")
    user_payload = {
        "analyst": {
            "password_sha256": hashlib.sha256(b"pass").hexdigest(),
            "roles": ["analyst", "viewer", "admin"],
        }
    }
    monkeypatch.setenv("AFOC_USERS_JSON", json.dumps(user_payload))
    core = ComposableIntelligenceCore()
    app = build_api(core)
    client = testclient.TestClient(app)
    login = client.post("/auth/login", json={"username": "analyst", "password": "pass"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_api_contract_endpoints(api_client: testclient.TestClient) -> None:
    allocation = api_client.post(
        "/allocate",
        json={"total_budget": 1000.0, "targets": {"architecture": 0.5, "ops": 0.5}},
    )
    assert allocation.status_code == 200
    body = allocation.json()
    assert "allocations" in body

    forecast = api_client.post("/forecast", json={"historical_spend": [100.0, 150.0, 175.0]})
    assert forecast.status_code == 200
    assert "predictions" in forecast.json()

    optimize = api_client.post("/optimize", json={"reward_history": [0.2, 0.5, 0.3]})
    assert optimize.status_code == 200
    optimise_body = optimize.json()
    assert "quantum_summary" in optimise_body
    assert optimise_body["quantum_summary"]["backend"]

    quantum = api_client.post("/optimize/quantum", json={"reward_history": [0.2, 0.5, 0.3]})
    assert quantum.status_code == 200
    q_body = quantum.json()
    assert "quantum_summary" in q_body
    assert "selected_action" in q_body

    audit = api_client.post("/audit")
    assert audit.status_code == 200
    assert "status" in audit.json()

    ingest = api_client.post("/ingest", json=[{"id": "x", "workload": "ops", "amount": 10.0}])
    assert ingest.status_code == 200
    assert ingest.json()["ingested"] >= 1

    health = api_client.get("/health")
    assert health.status_code == 200
    assert "event_bus" in health.json()


def test_api_rejects_invalid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AFOC_APP_SECRET", "test-secret")
    monkeypatch.setenv("AFOC_AUDIT_HMAC_SECRET", "audit-secret")
    core = ComposableIntelligenceCore()
    app = build_api(core)
    client = testclient.TestClient(app)

    response = client.post(
        "/allocate",
        json={"total_budget": 1000.0, "targets": {"architecture": 1.0}},
    )
    assert response.status_code == 401
