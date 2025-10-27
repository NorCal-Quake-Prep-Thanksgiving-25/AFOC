"""Health checks for orchestrator."""

import pytest

pytest.importorskip("sqlalchemy")

from afoc.orchestrator.health import liveness, readiness


def test_liveness_and_readiness():
    live = liveness()
    assert live["alive"] is True
    ready = readiness()
    assert "ready" in ready
    assert "pending_events" in ready
