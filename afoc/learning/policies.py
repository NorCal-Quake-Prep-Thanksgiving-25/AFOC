"""Adaptive policy management built on telemetry feedback."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import TYPE_CHECKING, Any, Dict

from .feedback import FeedbackSnapshot

if TYPE_CHECKING:  # pragma: no cover - static typing only
    from ..telemetry.bus import publish
    from ..telemetry.events import Severity, ValuationEvent
else:
    try:  # pragma: no cover - optional dependency guard
        from ..telemetry.bus import publish
        from ..telemetry.events import Severity, ValuationEvent
    except (
        ModuleNotFoundError
    ):  # pragma: no cover - fallback when telemetry deps missing
        from enum import Enum

        def publish(*_args: Any, **_kwargs: Any) -> None:
            return None

        class Severity(Enum):
            INFO = "info"

        class ValuationEvent:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                self.payload = kwargs.get("payload", {})


@dataclass
class PolicyState:
    """Capture the tunable parameters for the analytics stack."""

    anomaly_sensitivity: float = 1.0
    rightsize_headroom: float = 0.15
    forecast_method: str = "ets"

    def model_dump(self) -> Dict[str, object]:
        return asdict(self)


_STATE = PolicyState()


def get_policy_state() -> PolicyState:
    """Return the current policy state."""

    return _STATE


def apply_policy_updates(snapshot: FeedbackSnapshot) -> PolicyState:
    """Adapt policy knobs based on recent feedback."""

    global _STATE
    updated = PolicyState(
        anomaly_sensitivity=_tune_anomaly(snapshot),
        rightsize_headroom=_tune_headroom(snapshot),
        forecast_method=_tune_forecast(snapshot),
    )
    updated_values = updated.model_dump()
    previous_values = _STATE.model_dump()
    diff: Dict[str, object] = {}
    for key, value in updated_values.items():
        if isinstance(value, (int, float)):
            previous = previous_values.get(key, 0.0)
            prev_numeric = (
                float(previous) if isinstance(previous, (int, float)) else 0.0
            )
            diff[key] = float(value) - prev_numeric
        else:
            diff[key] = value
    _STATE = updated
    publish(
        ValuationEvent(
            scope="policy",
            severity=Severity.INFO,
            payload={"snapshot": snapshot.__dict__, "delta": diff},
            dedupe_key=None,
        )
    )
    return _STATE


def _tune_anomaly(snapshot: FeedbackSnapshot) -> float:
    baseline = _STATE.anomaly_sensitivity
    if snapshot.anomaly_false_positive_rate > 0.2:
        return max(baseline * 0.9, 0.5)
    if snapshot.anomaly_false_negative_rate > 0.1:
        return min(baseline * 1.1, 2.0)
    return baseline


def _tune_headroom(snapshot: FeedbackSnapshot) -> float:
    baseline = _STATE.rightsize_headroom
    if snapshot.realised_savings > 100000:
        return max(baseline * 0.9, 0.05)
    if snapshot.average_savings_ratio < 0.05:
        return min(baseline * 1.1, 0.4)
    return baseline


def _tune_forecast(snapshot: FeedbackSnapshot) -> str:
    baseline = _STATE.forecast_method
    if snapshot.forecast_mape > 25:
        return "prophet"
    if snapshot.forecast_mape < 10:
        return "ets"
    return baseline


__all__ = ["PolicyState", "get_policy_state", "apply_policy_updates"]
