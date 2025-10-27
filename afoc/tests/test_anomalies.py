"""Tests for the anomaly detection service."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

try:  # pragma: no cover - optional dependency guard
    import numpy as np
    from afoc.services import anomalies as anomaly_service
except ImportError:  # pragma: no cover - skip when scientific stack unavailable
    np = None  # type: ignore
    anomaly_service = None  # type: ignore

pytestmark = pytest.mark.skipif(
    anomaly_service is None or np is None,
    reason="scientific dependencies not available",
)


def _synthetic_usage() -> tuple[list[dict], set[int]]:
    base = datetime(2024, 1, 1)
    anomalies = {20, 45}
    records: list[dict] = []
    for offset in range(60):
        ts = base + timedelta(days=offset)
        seasonal = 100 + 10 * np.sin(offset / 6.0)
        cost = seasonal
        if offset in anomalies:
            cost += 80
        records.append(
            {
                "ts": ts,
                "provider": "aws",
                "account": "123456789012",
                "service": "compute",
                "cost_usd": float(round(cost, 2)),
            }
        )
    return records, anomalies


def test_detect_anomalies_precision_recall() -> None:
    """The detector should identify injected spikes with good fidelity."""

    records, expected_indices = _synthetic_usage()
    detected = anomaly_service.detect_anomalies(records)

    predicted_indices = {
        (anom.ts - datetime(2024, 1, 1)).days
        for anom in detected
        if anom.scope[2] == "compute"
    }
    true_positives = predicted_indices & expected_indices
    precision = len(true_positives) / max(len(predicted_indices), 1)
    recall = len(true_positives) / len(expected_indices)

    assert precision >= 0.7
    assert recall >= 0.7


def test_detect_anomalies_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """The fallback mode should trigger when sklearn is unavailable."""

    records, _ = _synthetic_usage()
    monkeypatch.setattr(anomaly_service, "IsolationForest", None)
    detected = anomaly_service.detect_anomalies(records)
    assert detected
    assert all(item.method == "robust_z" for item in detected)
