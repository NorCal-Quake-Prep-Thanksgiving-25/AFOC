"""Forecast agent implementing advanced Bayesian forecasting primitives."""

from __future__ import annotations

from statistics import fmean, pstdev
from typing import Dict, List

from ..intelligence import (
    AdaptiveSmoother,
    BayesianForecaster,
    ConfidenceInterval,
    StreamingAnomalyDetector,
)
from ..pydantic_compat import BaseModel, Field

from .event_bus import AgentEvent, AsyncEventBus


class ForecastRequest(BaseModel):
    historical_spend: List[float] = Field(default_factory=list)
    projected_events: int = 30
    confidence: float = Field(default=0.9, ge=0.5, le=0.99)


class ForecastDiagnostics(BaseModel):
    confidence_bandwidth: float = 0.0
    anomaly_rate: float = 0.0
    volatility: float = 0.0
    signal_to_noise: float = 0.0


class ForecastResponse(BaseModel):
    mean: float
    upper: float
    lower: float
    anomalies: List[int]
    predictions: List[float]
    intervals: List[Dict[str, float]]
    ensemble_predictions: List[float]
    diagnostics: ForecastDiagnostics


class ForecastAgent:
    """Produces forecasts and anomaly signals."""

    def __init__(self, event_bus: AsyncEventBus | None = None) -> None:
        self._event_bus = event_bus
        self._forecaster = BayesianForecaster()
        self._detector = StreamingAnomalyDetector()
        self._smoother = AdaptiveSmoother()
        if event_bus:
            event_bus.subscribe("forecast.completed", self._noop)

    def bind_event_bus(self, event_bus: AsyncEventBus) -> None:
        self._event_bus = event_bus
        event_bus.subscribe("forecast.completed", self._noop)

    async def forecast(self, request: ForecastRequest) -> ForecastResponse:
        posterior = self._forecaster.update(request.historical_spend, confidence=request.confidence)
        intervals = self._forecaster.multi_step_forecast(
            request.projected_events, confidence=request.confidence
        )
        anomalies = self._detector.detect(request.historical_spend)
        level, trend = self._smoother.update(request.historical_spend)
        smoothed = self._smoother.forecast(request.projected_events)
        predictions = [interval.mean for interval in intervals]
        ensemble_predictions = _blend_predictions(predictions, smoothed)
        diagnostics = _compute_diagnostics(
            history=request.historical_spend,
            intervals=intervals,
            anomalies=anomalies,
            level=level,
            trend=trend,
        )
        response = ForecastResponse(
            mean=posterior.mean,
            upper=posterior.upper,
            lower=posterior.lower,
            anomalies=anomalies,
            predictions=predictions,
            intervals=[_serialise_interval(interval) for interval in intervals],
            ensemble_predictions=ensemble_predictions,
            diagnostics=diagnostics,
        )
        if self._event_bus:
            await self._event_bus.publish(
                AgentEvent(type="forecast.completed", payload=response.dict())
            )
        return response

    async def _noop(self, event: AgentEvent) -> None:  # pragma: no cover - async hook
        return None


def _serialise_interval(interval: ConfidenceInterval) -> Dict[str, float]:
    return {
        "mean": interval.mean,
        "lower": interval.lower,
        "upper": interval.upper,
    }


def _blend_predictions(bayesian: List[float], smoothed: List[float]) -> List[float]:
    if not bayesian and not smoothed:
        return []
    if not smoothed:
        return list(bayesian)
    if not bayesian:
        return list(smoothed)
    length = min(len(bayesian), len(smoothed))
    ensemble = []
    for index in range(length):
        weight = 0.6 if index == 0 else 0.5
        ensemble.append(weight * bayesian[index] + (1 - weight) * smoothed[index])
    if len(bayesian) > length:
        ensemble.extend(bayesian[length:])
    elif len(smoothed) > length:
        ensemble.extend(smoothed[length:])
    return ensemble


def _compute_diagnostics(
    *,
    history: List[float],
    intervals: List[ConfidenceInterval],
    anomalies: List[int],
    level: float,
    trend: float,
) -> ForecastDiagnostics:
    if not history:
        return ForecastDiagnostics()
    widths = [interval.width for interval in intervals] or [0.0]
    mean_prediction = fmean(interval.mean for interval in intervals) if intervals else 0.0
    confidence_bandwidth = fmean(widths) / max(abs(mean_prediction), 1e-6)
    anomaly_rate = len(anomalies) / max(len(history), 1)
    volatility = pstdev(history) if len(history) > 1 else 0.0
    signal_to_noise = (abs(level) + abs(trend)) / max(volatility, 1e-6)
    return ForecastDiagnostics(
        confidence_bandwidth=confidence_bandwidth,
        anomaly_rate=anomaly_rate,
        volatility=volatility,
        signal_to_noise=signal_to_noise,
    )
