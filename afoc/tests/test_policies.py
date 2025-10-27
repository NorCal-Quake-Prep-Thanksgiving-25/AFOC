"""Adaptive policy tests."""

import pytest

pytest.importorskip("sqlalchemy")

from afoc.learning import policies
from afoc.learning.feedback import FeedbackSnapshot


def test_policy_updates_adjust_knobs():
    policies._STATE = policies.PolicyState()  # type: ignore[attr-defined]
    snapshot = FeedbackSnapshot(
        anomaly_false_positive_rate=0.3,
        anomaly_false_negative_rate=0.0,
        average_savings_ratio=0.03,
        realised_savings=150_000,
        forecast_mape=30.0,
    )
    updated = policies.apply_policy_updates(snapshot)
    assert updated.anomaly_sensitivity < 1.0
    assert updated.rightsize_headroom < 0.15
    assert updated.forecast_method == "prophet"
