"""Forecast agent implementing advanced Bayesian forecasting primitives."""

from __future__ import annotations

from typing import Dict, List

from ..intelligence import BayesianForecaster, ConfidenceInterval, StreamingAnomalyDetector
from ..pydantic_compat import BaseModel, Field

from .event_bus import AgentEvent, AsyncEventBus


class ForecastRequest(BaseModel):
    historical_spend: List[float] = Field(default_factory=list)
    projected_events: int = 30
    confidence: float = Field(default=0.9, ge=0.5, le=0.99)


class ForecastResponse(BaseModel):
    mean: float
    upper: float
    lower: float
    anomalies: List[int]
    predictions: List[float]
    intervals: List[Dict[str, float]]


class ForecastAgent:
    """Produces forecasts and anomaly signals."""

    def __init__(self, event_bus: AsyncEventBus | None = None) -> None:
        self._event_bus = event_bus
        self._forecaster = BayesianForecaster()
        self._detector = StreamingAnomalyDetector()
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
        response = ForecastResponse(
            mean=posterior.mean,
            upper=posterior.upper,
            lower=posterior.lower,
            anomalies=anomalies,
            predictions=[interval.mean for interval in intervals],
            intervals=[_serialise_interval(interval) for interval in intervals],
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
