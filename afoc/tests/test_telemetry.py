"""Tests for telemetry store and proof aggregation."""

from datetime import datetime, timedelta

import pytest

pytest.importorskip("sqlalchemy")

from afoc.services import aggregator
from afoc.telemetry import TelemetryEvent, TelemetryStore


def test_telemetry_records_and_summarises(tmp_path):
    store = TelemetryStore(url=f"sqlite:///{tmp_path / 'telemetry.sqlite'}")
    now = datetime.utcnow()
    store.record_events(
        [
            TelemetryEvent(
                recorded_at=now - timedelta(days=1),
                event_type="rightsizing",
                scope="r-1",
                before_value=10.0,
                after_value=6.0,
                delta_value=-4.0,
                metadata={"savings_ratio": 0.4},
            ),
            TelemetryEvent(
                recorded_at=now - timedelta(days=2),
                event_type="anomaly",
                scope="aws/acct/compute",
                before_value=100.0,
                after_value=150.0,
                delta_value=50.0,
                metadata={"score": 3.2},
            ),
        ]
    )
    summary = store.summarise(days=7)
    assert summary["overall"]["before"] == 110.0
    assert summary["overall"]["after"] == 156.0
    proof = aggregator.proof(window_days=7)
    assert proof["window_days"] == 7
    assert "annualised_value" in proof
