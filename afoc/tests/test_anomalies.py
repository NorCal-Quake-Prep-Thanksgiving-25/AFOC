"""Tests for anomaly services."""

from afoc.services import anomalies


def test_detect_anomalies_returns_list() -> None:
    """Ensure the anomaly detector returns a list."""

    result = anomalies.detect_anomalies([{"value": 1}])
    assert isinstance(result, list)
