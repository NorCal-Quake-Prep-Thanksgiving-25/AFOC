"""Telemetry collection and adaptive control utilities."""

from .adaptive import AdaptiveController
from .bus import consume, publish, publish_many
from .events import (
    AnomalyEvent,
    BaseEvent,
    ErrorEvent,
    ForecastEvent,
    RightsizeEvent,
    Severity,
    ValuationEvent,
)

from typing import Any, Optional

TelemetryEvent: Optional[Any]
TelemetryStore: Optional[Any]

try:  # pragma: no cover - optional dependency guard
    from .store import (
        TelemetryEvent as _TelemetryEvent,
        TelemetryStore as _TelemetryStore,
    )
except ModuleNotFoundError:  # pragma: no cover - fallback when SQLAlchemy absent
    TelemetryEvent = None
    TelemetryStore = None
else:
    TelemetryEvent = _TelemetryEvent
    TelemetryStore = _TelemetryStore

__all__ = [
    "BaseEvent",
    "AnomalyEvent",
    "RightsizeEvent",
    "ForecastEvent",
    "ValuationEvent",
    "ErrorEvent",
    "Severity",
    "publish",
    "publish_many",
    "consume",
    "TelemetryEvent",
    "TelemetryStore",
    "AdaptiveController",
]
