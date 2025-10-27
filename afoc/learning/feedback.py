"""Feedback utilities derived from telemetry events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Optional


@dataclass
class FeedbackSnapshot:
    """Aggregated metrics from telemetry for adaptive policies."""

    anomaly_false_positive_rate: float = 0.0
    anomaly_false_negative_rate: float = 0.0
    average_savings_ratio: float = 0.0
    realised_savings: float = 0.0
    forecast_mape: float = 0.0


def _extract(metric: str, records: Iterable[Mapping[str, object]]) -> list[float]:
    values: list[float] = []
    for record in records:
        value = record.get(metric)
        if isinstance(value, (int, float)):
            values.append(float(value))
    return values


def realised_savings_delta(records: Iterable[Mapping[str, object]]) -> float:
    """Return the cumulative realised savings from rightsizing events."""

    return sum(_extract("savings", records))


def forecast_error(records: Iterable[Mapping[str, object]]) -> Optional[float]:
    """Return the average MAPE recorded by forecasting events."""

    values = _extract("mape", records)
    if not values:
        return None
    return sum(values) / len(values)


def build_snapshot(
    *,
    rightsizing: Iterable[Mapping[str, object]],
    forecasting: Iterable[Mapping[str, object]],
    anomalies: Iterable[Mapping[str, object]],
) -> FeedbackSnapshot:
    """Aggregate telemetry payloads into a feedback snapshot."""

    savings = realised_savings_delta(rightsizing)
    mape = forecast_error(forecasting) or 0.0
    anomaly_scores = _extract("score", anomalies)
    false_positive_rate = (
        sum(1 for score in anomaly_scores if score < 0) / len(anomaly_scores)
        if anomaly_scores
        else 0.0
    )
    false_negative_rate = (
        sum(1 for score in anomaly_scores if score > 10) / len(anomaly_scores)
        if anomaly_scores
        else 0.0
    )
    average_ratio_values = _extract("savings_ratio", rightsizing)
    average_ratio = (
        sum(average_ratio_values) / len(average_ratio_values)
        if average_ratio_values
        else 0.0
    )
    return FeedbackSnapshot(
        anomaly_false_positive_rate=false_positive_rate,
        anomaly_false_negative_rate=false_negative_rate,
        average_savings_ratio=average_ratio,
        realised_savings=savings,
        forecast_mape=mape,
    )


__all__ = [
    "FeedbackSnapshot",
    "realised_savings_delta",
    "forecast_error",
    "build_snapshot",
]
