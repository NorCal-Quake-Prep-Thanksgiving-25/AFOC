"""Telemetry bus integration tests."""

from datetime import datetime

import pytest

pytest.importorskip("sqlalchemy")

from afoc.db import session_scope
from afoc.db.models import TelemetryDeadLetter, TelemetryEventRecord
from afoc.telemetry.bus import consume, publish
from afoc.telemetry.events import AnomalyEvent, ErrorEvent, Severity


@pytest.mark.usefixtures("_isolate_database")
def test_publish_is_idempotent():
    event = AnomalyEvent(
        scope="aws/demo/compute",
        severity=Severity.WARN,
        payload={"observed": 150.0, "expected": 100.0, "score": 3.5},
        dedupe_key="anomaly:demo:2024-01-01",
        ts=datetime(2024, 1, 1),
    )
    publish(event)
    publish(event)
    with session_scope() as session:
        count = session.query(TelemetryEventRecord).count()
    assert count == 1


@pytest.mark.usefixtures("_isolate_database")
def test_consume_acknowledges_event():
    publish(
        AnomalyEvent(
            scope="demo",
            severity=Severity.WARN,
            payload={"observed": 200.0, "expected": 100.0},
        )
    )
    envelopes = list(consume())
    assert envelopes
    envelopes[0].ack()
    with session_scope() as session:
        record = session.get(TelemetryEventRecord, envelopes[0].id)
        assert record.processed is True


@pytest.mark.usefixtures("_isolate_database")
def test_consume_dead_letter_on_failure():
    publish(ErrorEvent(scope="demo", payload={"error": "boom"}, dedupe_key="err:demo"))
    envelope = next(iter(consume()))
    envelope.nack("processing failed")
    with session_scope() as session:
        dlq_count = session.query(TelemetryDeadLetter).count()
    assert dlq_count == 1


@pytest.mark.usefixtures("_isolate_database")
def test_consume_orders_events_by_timestamp():
    publish(
        AnomalyEvent(
            scope="demo/first",
            severity=Severity.WARN,
            payload={"sequence": 1},
            ts=datetime(2024, 1, 1, 8, 0, 0),
        )
    )
    publish(
        AnomalyEvent(
            scope="demo/second",
            severity=Severity.WARN,
            payload={"sequence": 2},
            ts=datetime(2024, 1, 1, 9, 0, 0),
        )
    )

    envelopes = list(consume())
    assert [env.event.payload["sequence"] for env in envelopes] == [1, 2]
