from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
testclient = pytest.importorskip("fastapi.testclient")

from afoc.api import build_api
from afoc.core import ComposableIntelligenceCore


def test_api_contract_endpoints() -> None:
    core = ComposableIntelligenceCore()
    app = build_api(core)
    client = testclient.TestClient(app)

    allocation = client.post(
        "/allocate",
        json={"total_budget": 1000.0, "targets": {"architecture": 0.5, "ops": 0.5}},
    )
    assert allocation.status_code == 200
    body = allocation.json()
    assert "allocations" in body

    forecast = client.post("/forecast", json={"historical_spend": [100.0, 150.0, 175.0]})
    assert forecast.status_code == 200
    assert "predictions" in forecast.json()

    optimize = client.post("/optimize", json={"reward_history": [0.2, 0.5, 0.3]})
    assert optimize.status_code == 200
    optimise_body = optimize.json()
    assert "quantum_summary" in optimise_body
    assert optimise_body["quantum_summary"]["backend"]

    quantum = client.post("/optimize/quantum", json={"reward_history": [0.2, 0.5, 0.3]})
    assert quantum.status_code == 200
    q_body = quantum.json()
    assert "quantum_summary" in q_body
    assert "selected_action" in q_body

    audit = client.post("/audit")
    assert audit.status_code == 200
    assert "status" in audit.json()

    ingest = client.post("/ingest", json=[{"id": "x", "workload": "ops", "amount": 10.0}])
    assert ingest.status_code == 200
    assert ingest.json()["ingested"] >= 1

    health = client.get("/health")
    assert health.status_code == 200
    assert "event_bus" in health.json()
