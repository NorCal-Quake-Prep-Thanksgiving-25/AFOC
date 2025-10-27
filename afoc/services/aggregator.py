"""Aggregation services for reporting."""

from __future__ import annotations

from typing import Dict, List, cast

try:  # pragma: no cover - optional dependency guard
    from ..telemetry import TelemetryStore
except RuntimeError:  # pragma: no cover - telemetry unavailable
    TelemetryStore = None  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - telemetry unavailable
    TelemetryStore = None  # type: ignore


def build_report(anomalies: List[dict], forecasts: List[float]) -> Dict[str, object]:
    """Combine anomalies, forecasts, and telemetry savings."""

    if TelemetryStore is None:
        summary = {
            "totals": {},
            "overall": {"before": 0.0, "after": 0.0, "delta": 0.0},
            "window_days": 90,
        }
    else:
        telemetry = TelemetryStore.default()
        summary = telemetry.summarise(days=90)
    return {
        "anomalies": anomalies,
        "forecast": forecasts,
        "telemetry": summary,
    }


def proof(window_days: int = 90) -> Dict[str, object]:
    """Return an ROI proof payload summarising savings."""

    if TelemetryStore is None:
        summary: Dict[str, object] = {
            "totals": {},
            "overall": {"before": 0.0, "after": 0.0, "delta": 0.0},
            "window_days": window_days,
        }
    else:
        telemetry = TelemetryStore.default()
        summary = telemetry.summarise(days=window_days)
    overall = cast(Dict[str, float], summary["overall"])
    before = float(overall.get("before", 0.0))
    after = float(overall.get("after", 0.0))
    delta = float(overall.get("delta", 0.0))
    savings = before - after
    improvement = (savings / before * 100.0) if before else 0.0
    return {
        "window_days": window_days,
        "before_cost": before,
        "after_cost": after,
        "delta": delta,
        "waste_prevented_percent": improvement,
        "annualised_value": savings * 12 / max(window_days, 1) * 30,
        "breakdown": summary["totals"],
    }


__all__ = ["build_report", "proof"]
