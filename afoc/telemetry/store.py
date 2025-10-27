"""Persistent telemetry store for cross-service analytics."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from os import getenv
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    create_engine,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Session

_TELEMETRY_PATH = Path("telemetry.db")


class _Base(DeclarativeBase):
    """Declarative base for telemetry models."""

    pass


class TelemetryEventModel(_Base):
    """SQLAlchemy model storing telemetry events."""

    __tablename__ = "telemetry_events"

    id = Column(Integer, primary_key=True)
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    event_type = Column(String(32), nullable=False)
    scope = Column(String(128), nullable=True)
    before_value = Column(Float, nullable=True)
    after_value = Column(Float, nullable=True)
    delta_value = Column(Float, nullable=True)
    metadata_json = Column("metadata", JSON, nullable=True)


@dataclass(frozen=True)
class TelemetryEvent:
    """Public representation of a telemetry event."""

    recorded_at: datetime
    event_type: str
    scope: str | None
    before_value: float | None
    after_value: float | None
    delta_value: float | None
    metadata: Dict[str, Any] | None


class TelemetryStore:
    """Stores telemetry in a lightweight SQLite database."""

    def __init__(self, url: str | None = None) -> None:
        default_url = getenv("AFOC_TELEMETRY_URL")
        self.url = url or default_url or f"sqlite:///{_TELEMETRY_PATH}"
        self._engine = create_engine(self.url, future=True)
        _Base.metadata.create_all(self._engine)

    @classmethod
    def default(cls) -> "TelemetryStore":
        """Return the default singleton telemetry store."""

        return cls()

    def _serialise_metadata(
        self, metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any] | None:
        if metadata is None:
            return None
        try:
            json.loads(json.dumps(metadata))  # ensure metadata is JSON serialisable
        except (TypeError, ValueError):
            return {"note": "non-serialisable metadata omitted"}
        return metadata

    def record_event(
        self,
        event_type: str,
        *,
        scope: str | None = None,
        before_value: float | None = None,
        after_value: float | None = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Persist a telemetry event with automatic delta computation."""

        delta = None
        if before_value is not None and after_value is not None:
            delta = after_value - before_value
        metadata = self._serialise_metadata(metadata)
        with Session(self._engine) as session:
            session.add(
                TelemetryEventModel(
                    event_type=event_type,
                    scope=scope,
                    before_value=before_value,
                    after_value=after_value,
                    delta_value=delta,
                    metadata_json=metadata,
                )
            )
            session.commit()

    def record_events(self, events: Iterable[TelemetryEvent]) -> None:
        """Persist multiple events efficiently."""

        models = [
            TelemetryEventModel(
                recorded_at=event.recorded_at,
                event_type=event.event_type,
                scope=event.scope,
                before_value=event.before_value,
                after_value=event.after_value,
                delta_value=event.delta_value,
                metadata_json=self._serialise_metadata(event.metadata),
            )
            for event in events
        ]
        if not models:
            return
        with Session(self._engine) as session:
            session.add_all(models)
            session.commit()

    def list_recent(
        self, event_type: str | None = None, *, days: int = 30
    ) -> List[TelemetryEvent]:
        """Return events within the requested lookback window."""

        cutoff = datetime.utcnow() - timedelta(days=days)
        stmt = select(TelemetryEventModel).where(
            TelemetryEventModel.recorded_at >= cutoff
        )
        if event_type is not None:
            stmt = stmt.where(TelemetryEventModel.event_type == event_type)
        stmt = stmt.order_by(TelemetryEventModel.recorded_at.desc())
        with Session(self._engine) as session:
            rows = session.execute(stmt).scalars().all()
        return [
            TelemetryEvent(
                recorded_at=row.recorded_at,
                event_type=row.event_type,
                scope=row.scope,
                before_value=row.before_value,
                after_value=row.after_value,
                delta_value=row.delta_value,
                metadata=row.metadata_json,
            )
            for row in rows
        ]

    def summarise(self, *, days: int = 30) -> Dict[str, Any]:
        """Return aggregate savings metrics for reporting."""

        events = self.list_recent(days=days)
        totals: Dict[str, Dict[str, float]] = {}
        for event in events:
            entry = totals.setdefault(
                event.event_type,
                {"before": 0.0, "after": 0.0, "delta": 0.0, "count": 0.0},
            )
            if event.before_value is not None:
                entry["before"] += float(event.before_value)
            if event.after_value is not None:
                entry["after"] += float(event.after_value)
            if event.delta_value is not None:
                entry["delta"] += float(event.delta_value)
            entry["count"] += 1
        overall = {
            "before": sum(item["before"] for item in totals.values()),
            "after": sum(item["after"] for item in totals.values()),
            "delta": sum(item["delta"] for item in totals.values()),
        }
        return {"totals": totals, "overall": overall, "window_days": days}

    def average_metric(
        self, event_type: str, metric: str, *, days: int = 30
    ) -> Optional[float]:
        """Return the average metadata metric for a given event type."""

        events = self.list_recent(event_type, days=days)
        values: List[float] = []
        for event in events:
            if not event.metadata:
                continue
            value = event.metadata.get(metric)
            if value is None:
                continue
            try:
                values.append(float(value))
            except (TypeError, ValueError):
                continue
        if not values:
            return None
        return sum(values) / len(values)


__all__ = ["TelemetryEvent", "TelemetryStore"]
