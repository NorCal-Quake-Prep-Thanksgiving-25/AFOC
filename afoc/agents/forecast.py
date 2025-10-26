"""Forecast agent implementing advanced Bayesian forecasting primitives."""

from __future__ import annotations

from statistics import fmean, pstdev
from typing import Dict, List

from ..intelligence import (
    AdaptiveSmoother,
    BayesianForecaster,
    ConfidenceInterval,
    IsolationForestDetector,
    StatsmodelsForecaster,
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
    ml_anomaly_rate: float = 0.0
    ensemble_divergence: float = 0.0
    seasonal_strength: float = 0.0


class ForecastResponse(BaseModel):
    mean: float
    upper: float
    lower: float
    anomalies: List[int]
    predictions: List[float]
    intervals: List[Dict[str, float]]
    ensemble_predictions: List[float]
    seasonal_predictions: List[float]
    diagnostics: ForecastDiagnostics


class ForecastAgent:
    """Produces forecasts and anomaly signals."""

    def __init__(self, event_bus: AsyncEventBus | None = None) -> None:
        self._event_bus = event_bus
        self._forecaster = BayesianForecaster()
        self._detector = StreamingAnomalyDetector()
        self._smoother = AdaptiveSmoother()
        self._ml_detector: IsolationForestDetector | None
        self._seasonal_model: StatsmodelsForecaster | None
        try:
            self._ml_detector = IsolationForestDetector()
        except Exception:  # pragma: no cover - optional dependency unavailable
            self._ml_detector = None
        try:
            self._seasonal_model = StatsmodelsForecaster()
        except Exception:  # pragma: no cover - optional dependency unavailable
            self._seasonal_model = None
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
        streaming_anomalies = self._detector.detect(request.historical_spend)
        ml_anomalies: List[int] = []
        if self._ml_detector is not None:
            try:
                ml_anomalies = self._ml_detector.detect(request.historical_spend)
            except Exception:  # pragma: no cover - runtime guard
                ml_anomalies = []
        anomalies = sorted(set(streaming_anomalies + ml_anomalies))
        level, trend = self._smoother.update(request.historical_spend)
        smoothed = self._smoother.forecast(request.projected_events)
        seasonal_predictions: List[float] = []
        if self._seasonal_model is not None:
            try:
                self._seasonal_model.fit(request.historical_spend)
                seasonal_predictions = self._seasonal_model.forecast(request.projected_events)
            except Exception:  # pragma: no cover - runtime guard
                seasonal_predictions = []
        predictions = [interval.mean for interval in intervals]
        ensemble_predictions = _blend_predictions(predictions, smoothed, seasonal_predictions)
        diagnostics = _compute_diagnostics(
            history=request.historical_spend,
            intervals=intervals,
            anomalies=anomalies,
            level=level,
            trend=trend,
            ml_anomalies=ml_anomalies,
            smoothed=smoothed,
            seasonal=seasonal_predictions,
        )
        response = ForecastResponse(
            mean=posterior.mean,
            upper=posterior.upper,
            lower=posterior.lower,
            anomalies=anomalies,
            predictions=predictions,
            intervals=[_serialise_interval(interval) for interval in intervals],
            ensemble_predictions=ensemble_predictions,
            seasonal_predictions=seasonal_predictions,
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


def _blend_predictions(
    bayesian: List[float], smoothed: List[float], seasonal: List[float]
) -> List[float]:
    if not bayesian and not smoothed and not seasonal:
        return []
    if not smoothed:
        baseline = list(bayesian)
    else:
        baseline = list(smoothed)
    if not bayesian:
        bayesian = [0.0 for _ in range(len(baseline))]
    if not smoothed:
        smoothed = [0.0 for _ in range(len(bayesian))]
    if not seasonal:
        seasonal = [0.0 for _ in range(max(len(bayesian), len(smoothed)))]
    length = min(len(bayesian), len(smoothed), len(seasonal) or len(bayesian))
    ensemble = []
    for index in range(length):
        weight_bayesian = 0.5 if index == 0 else 0.4
        weight_seasonal = 0.2
        weight_smoothed = 1.0 - weight_bayesian - weight_seasonal
        ensemble.append(
            weight_bayesian * bayesian[index]
            + weight_smoothed * smoothed[index]
            + weight_seasonal * seasonal[index]
        )
    if len(bayesian) > length:
        ensemble.extend(bayesian[length:])
    elif len(smoothed) > length:
        ensemble.extend(smoothed[length:])
    elif len(seasonal) > length:
        ensemble.extend(seasonal[length:])
    return ensemble


def _compute_diagnostics(
    *,
    history: List[float],
    intervals: List[ConfidenceInterval],
    anomalies: List[int],
    level: float,
    trend: float,
    ml_anomalies: List[int],
    smoothed: List[float],
    seasonal: List[float],
) -> ForecastDiagnostics:
    if not history:
        return ForecastDiagnostics()
    widths = [interval.width for interval in intervals] or [0.0]
    mean_prediction = fmean(interval.mean for interval in intervals) if intervals else 0.0
    confidence_bandwidth = fmean(widths) / max(abs(mean_prediction), 1e-6)
    anomaly_rate = len(anomalies) / max(len(history), 1)
    volatility = pstdev(history) if len(history) > 1 else 0.0
    signal_to_noise = (abs(level) + abs(trend)) / max(volatility, 1e-6)
    ml_rate = len(ml_anomalies) / max(len(history), 1)
    divergence = 0.0
    if smoothed and seasonal:
        paired = zip(smoothed, seasonal)
        divergence = fmean(abs(a - b) for a, b in paired) / max(abs(level) + abs(trend), 1e-6)
    seasonal_strength = 0.0
    if seasonal:
        seasonal_strength = pstdev(seasonal) / max(pstdev(history) or 1e-6, 1e-6)
    return ForecastDiagnostics(
        confidence_bandwidth=confidence_bandwidth,
        anomaly_rate=anomaly_rate,
        volatility=volatility,
        signal_to_noise=signal_to_noise,
        ml_anomaly_rate=ml_rate,
        ensemble_divergence=divergence,
        seasonal_strength=seasonal_strength,
    )
