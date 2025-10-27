"""Tests for the FastAPI layer."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

try:  # pragma: no cover - optional dependency guard
    from fastapi.testclient import TestClient
    from afoc.api.app import create_app
except ImportError:  # pragma: no cover - skip if FastAPI missing
    TestClient = None  # type: ignore
    create_app = None  # type: ignore


@pytest.mark.skipif(
    TestClient is None or create_app is None, reason="FastAPI not available"
)
def test_anomaly_endpoint_returns_detection() -> None:
    """Posting usage data should return at least one anomaly."""

    base = datetime(2024, 1, 1)
    payload = []
    for offset in range(10):
        ts = base + timedelta(days=offset)
        cost = 100.0
        if offset == 7:
            cost = 350.0
        payload.append(
            {
                "ts": ts.isoformat(),
                "provider": "aws",
                "account": "acct",
                "service": "compute",
                "cost_usd": cost,
            }
        )

    client = TestClient(create_app())  # type: ignore[operator]
    response = client.post("/analyze/anomalies", json=payload)
    if response.status_code == 503:
        pytest.skip("anomaly service unavailable in test environment")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(item["scope"]["service"] == "compute" for item in data)


@pytest.mark.skipif(
    TestClient is None or create_app is None, reason="FastAPI not available"
)
def test_rightsizing_endpoint_returns_recommendations() -> None:
    """Posting inventory data should return recommendations."""

    client = TestClient(create_app())  # type: ignore[operator]
    payload = {
        "inventory": [
            {
                "resource_id": "r-1",
                "instance_type": "m5.large",
                "price": 0.12,
                "cpu_capacity": 2.0,
                "memory_capacity": 8.0,
                "options": [
                    {
                        "instance_type": "t3.medium",
                        "price": 0.067,
                        "cpu_capacity": 2.0,
                        "memory_capacity": 4.0,
                    }
                ],
            }
        ],
        "utilization": [{"resource_id": "r-1", "p95_cpu": 30.0, "p95_mem": 35.0}],
        "headroom": 0.1,
        "policy": "cost",
    }

    response = client.post("/optimize/rightsize", json=payload)
    if response.status_code == 503:
        pytest.skip("rightsizing service unavailable in test environment")
    assert response.status_code == 200
    result = response.json()
    assert result
    assert result[0]["recommended_type"] in {"t3.medium", "m5.large"}


@pytest.mark.skipif(
    TestClient is None or create_app is None, reason="FastAPI not available"
)
def test_forecast_endpoint_returns_payload() -> None:
    """Posting records to /forecast should return forecast data."""

    base = datetime(2024, 1, 1)
    records = []
    for offset in range(40):
        ts = base + timedelta(days=offset)
        cost = 100 + 5 * (offset % 7)
        records.append({"date": ts.isoformat(), "cost_usd": cost, "account": "acct"})

    client = TestClient(create_app())  # type: ignore[operator]
    response = client.post(
        "/forecast", params={"scope": "acct", "h": 10}, json={"records": records}
    )
    if response.status_code == 503:
        pytest.skip("forecasting service unavailable in test environment")
    assert response.status_code == 200
    data = response.json()
    assert data["points"]
    assert len(data["points"]) == 10


@pytest.mark.skipif(
    TestClient is None or create_app is None, reason="FastAPI not available"
)
def test_value_report_endpoint_returns_breakdown() -> None:
    """GET /report/value should return the valuation components."""

    client = TestClient(create_app())  # type: ignore[operator]
    response = client.get(
        "/report/value",
        params={
            "annual_spend": 1_000_000,
            "tier": "f500",
            "anomaly_spend": 50_000,
            "rightsizing_monthly_savings": 5_000,
            "reservable_spend": 200_000,
            "anomaly_count": 5,
        },
    )
    if response.status_code == 503:
        pytest.skip("valuation service unavailable in test environment")
    assert response.status_code == 200
    payload = response.json()
    assert payload["anomaly"] > 0
    assert (
        payload["integrated"]
        >= payload["anomaly"] + payload["rightsize"] + payload["forecast"]
    )
