"""Forecast agent implementing Bayesian spend estimation and anomaly detection."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import math
from ..pydantic_compat import BaseModel, Field

from .event_bus import AgentEvent, AsyncEventBus

try:  # pragma: no cover - optional dependency
    from sklearn.ensemble import IsolationForest  # type: ignore
except Exception:  # pragma: no cover - fallback
    IsolationForest = None


class ForecastRequest(BaseModel):
    historical_spend: List[float] = Field(default_factory=list)
    projected_events: int = 30
    confidence: float = Field(default=0.9, ge=0.5, le=0.99)


class ForecastResponse(BaseModel):
    mean: float
    upper: float
    lower: float
    anomalies: List[int]


@dataclass
class _BayesianPosterior:
    mean: float
    precision: float


class ForecastAgent:
    """Produces forecasts and anomaly signals."""

    def __init__(self, event_bus: AsyncEventBus | None = None) -> None:
        self._event_bus = event_bus
        self._posterior: _BayesianPosterior | None = None
        if event_bus:
            event_bus.subscribe("forecast.completed", self._noop)

    def bind_event_bus(self, event_bus: AsyncEventBus) -> None:
        self._event_bus = event_bus
        event_bus.subscribe("forecast.completed", self._noop)

    async def forecast(self, request: ForecastRequest) -> ForecastResponse:
        posterior = self._update_posterior(request.historical_spend)
        variance = 1.0 / max(posterior.precision, 1e-6)
        std = math.sqrt(variance)
        z = self._z_score(request.confidence)
        mean = posterior.mean
        response = ForecastResponse(
            mean=mean,
            upper=mean + z * std,
            lower=max(0.0, mean - z * std),
            anomalies=self._detect_anomalies(request.historical_spend),
        )
        if self._event_bus:
            await self._event_bus.publish(
                AgentEvent(type="forecast.completed", payload=response.dict())
            )
        return response

    def _update_posterior(self, samples: List[float]) -> _BayesianPosterior:
        prior = self._posterior or _BayesianPosterior(mean=1000.0, precision=1.0)
        if not samples:
            self._posterior = prior
            return prior
        precision = prior.precision
        mean = prior.mean
        for sample in samples:
            precision += 1.0
            mean += (sample - mean) / precision
        self._posterior = _BayesianPosterior(mean=mean, precision=precision)
        return self._posterior

    def _detect_anomalies(self, samples: List[float]) -> List[int]:
        if not samples:
            return []
        if IsolationForest is None or len(samples) < 8:
            mean = sum(samples) / len(samples)
            variance = sum((x - mean) ** 2 for x in samples) / max(len(samples) - 1, 1)
            std = math.sqrt(variance)
            return [i for i, value in enumerate(samples) if abs(value - mean) > 3 * std]
        model = IsolationForest(contamination="auto", random_state=42)
        data = [[value] for value in samples]
        flags = model.fit_predict(data)
        return [i for i, flag in enumerate(flags) if flag == -1]

    async def _noop(self, event: AgentEvent) -> None:  # pragma: no cover - async hook
        return None

    def _z_score(self, confidence: float) -> float:
        """Approximate Z score using inverse error function."""

        from statistics import NormalDist

        clamped = min(max(confidence, 0.5), 0.999)
        return NormalDist().inv_cdf(clamped)
