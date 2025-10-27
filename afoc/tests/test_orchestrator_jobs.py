"""Tests for orchestrator jobs."""

import pytest

pytest.importorskip("sqlalchemy")

from afoc.db import session_scope
from afoc.db.models import TelemetryEventRecord
from afoc.orchestrator import jobs


def _count(event_type: str) -> int:
    with session_scope() as session:
        return (
            session.query(TelemetryEventRecord)
            .filter(TelemetryEventRecord.event_type == event_type)
            .count()
        )


def test_jobs_are_idempotent():
    jobs.run_ingest()
    jobs.run_ingest()
    jobs.run_anomalies()
    jobs.run_anomalies()
    jobs.run_rightsizing()
    jobs.run_rightsizing()
    jobs.run_forecasting()
    jobs.run_forecasting()
    jobs.run_valuation()
    jobs.run_valuation()

    assert _count("anomaly") <= 1
    assert _count("rightsize") <= 1
    assert _count("forecast") <= 1
    assert _count("valuation") <= 4  # ingest + valuation + policy feedback events
