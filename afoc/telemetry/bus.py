"""Database-backed telemetry bus with idempotent publishing."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, Iterator, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_session_factory, session_scope
from ..db.models import TelemetryDeadLetter, TelemetryEventRecord
from .events import BaseEvent, ErrorEvent
from .metrics import increment_counter

_LOGGER = logging.getLogger(__name__)


@dataclass
class TelemetryEnvelope:
    """Wrapper providing ack/nack semantics for telemetry consumers."""

    id: int
    event: BaseEvent

    def ack(self) -> None:
        """Mark the event as processed."""

        with session_scope() as session:
            record = session.get(TelemetryEventRecord, self.id)
            if record:
                record.processed = True
                session.add(record)

    def nack(self, reason: str) -> None:
        """Send the event to the dead-letter queue with a reason."""

        with session_scope() as session:
            record = session.get(TelemetryEventRecord, self.id)
            if not record:
                return
            record.processed = True
            session.add(record)
            session.add(
                TelemetryDeadLetter(
                    event_id=record.id, reason=reason, payload=record.payload
                )
            )


def publish(event: BaseEvent) -> None:
    """Persist an event in the telemetry queue with dedupe semantics."""

    payload = {
        "ts": event.ts,
        "scope": event.scope,
        "severity": event.severity.value,
        "payload": event.payload,
        "dedupe_key": event.dedupe_key,
    }

    with session_scope() as session:
        if event.dedupe_key:
            existing = _find_by_dedupe(session, event.dedupe_key)
            if existing:
                return
        record = TelemetryEventRecord(
            event_type=event.event_type,
            **payload,
        )
        session.add(record)
        try:
            session.flush()
        except IntegrityError as exc:  # pragma: no cover - defensive guard
            session.rollback()
            _LOGGER.debug("Duplicate telemetry event skipped", exc_info=exc)
            return
    increment_counter(f"telemetry.published.{event.event_type}")


def publish_many(events: Iterable[BaseEvent]) -> None:
    """Publish a batch of events efficiently."""

    for event in events:
        publish(event)


def consume(batch_size: int = 500) -> Iterator[TelemetryEnvelope]:
    """Yield telemetry events awaiting processing."""

    session_factory = get_session_factory()
    with session_factory() as session:
        stmt = (
            select(TelemetryEventRecord)
            .where(TelemetryEventRecord.processed.is_(False))
            .order_by(TelemetryEventRecord.ts.asc())
            .limit(batch_size)
        )
        for record in session.execute(stmt).scalars():
            event = _materialise_event(record)
            yield TelemetryEnvelope(id=record.id, event=event)


def _materialise_event(record: TelemetryEventRecord) -> BaseEvent:
    payload = {
        "ts": record.ts,
        "scope": record.scope,
        "severity": record.severity,
        "payload": record.payload or {},
        "dedupe_key": record.dedupe_key,
    }
    if isinstance(payload["severity"], str):
        payload["severity"] = payload["severity"]
    try:
        return BaseEvent.from_record(record.event_type, payload)
    except Exception as exc:  # pragma: no cover - defensive fallback
        _LOGGER.exception(
            "Failed to hydrate event; routing to error event", exc_info=exc
        )
        return ErrorEvent(
            scope=record.scope, payload=payload, dedupe_key=record.dedupe_key
        )


def _find_by_dedupe(
    session: Session, dedupe_key: str
) -> Optional[TelemetryEventRecord]:
    return (
        session.execute(
            select(TelemetryEventRecord).where(
                TelemetryEventRecord.dedupe_key == dedupe_key
            )
        )
        .scalars()
        .first()
    )


__all__ = ["publish", "publish_many", "consume", "TelemetryEnvelope"]
