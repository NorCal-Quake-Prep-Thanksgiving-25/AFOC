"""Telemetry event models for the unified event bus."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, ClassVar, Dict, Optional, Type

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Enumerate telemetry severities."""

    INFO = "info"
    WARN = "warn"
    CRITICAL = "critical"


class BaseEvent(BaseModel):
    """Base telemetry event emitted by analytics services."""

    ts: datetime = Field(default_factory=datetime.utcnow)
    scope: str = Field(..., min_length=1)
    severity: Severity = Severity.INFO
    payload: Dict[str, Any] = Field(default_factory=dict)
    dedupe_key: Optional[str] = None

    event_type: ClassVar[str] = "event"

    def model_dump_payload(self) -> Dict[str, Any]:
        """Return a JSON-serialisable payload for persistence."""

        return {
            "ts": self.ts,
            "scope": self.scope,
            "severity": self.severity.value,
            "payload": self.payload,
            "dedupe_key": self.dedupe_key,
        }

    @classmethod
    def from_record(cls, event_type: str, data: Dict[str, Any]) -> "BaseEvent":
        """Rehydrate an event from database payload."""

        model_cls = EVENT_REGISTRY.get(event_type, GenericEvent)
        return model_cls(**data)


class AnomalyEvent(BaseEvent):
    """Event raised when anomalies are detected."""

    event_type: ClassVar[str] = "anomaly"


class RightsizeEvent(BaseEvent):
    """Event raised after right-sizing recommendations."""

    event_type: ClassVar[str] = "rightsize"


class ForecastEvent(BaseEvent):
    """Event raised after forecasting pipelines."""

    event_type: ClassVar[str] = "forecast"


class ValuationEvent(BaseEvent):
    """Event raised after valuation is computed."""

    event_type: ClassVar[str] = "valuation"


class ErrorEvent(BaseEvent):
    """Event raised for operational errors."""

    event_type: ClassVar[str] = "error"
    severity: Severity = Severity.CRITICAL


class GenericEvent(BaseEvent):
    """Fallback event when a specialised model is unavailable."""

    event_type: ClassVar[str] = "generic"


EVENT_REGISTRY: Dict[str, Type[BaseEvent]] = {
    AnomalyEvent.event_type: AnomalyEvent,
    RightsizeEvent.event_type: RightsizeEvent,
    ForecastEvent.event_type: ForecastEvent,
    ValuationEvent.event_type: ValuationEvent,
    ErrorEvent.event_type: ErrorEvent,
}


__all__ = [
    "BaseEvent",
    "AnomalyEvent",
    "RightsizeEvent",
    "ForecastEvent",
    "ValuationEvent",
    "ErrorEvent",
    "Severity",
    "EVENT_REGISTRY",
]
