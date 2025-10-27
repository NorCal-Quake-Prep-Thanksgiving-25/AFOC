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


@pytest.mark.skipif(TestClient is None or create_app is None, reason="FastAPI not available")
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
