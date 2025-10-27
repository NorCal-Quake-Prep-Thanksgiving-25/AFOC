"""Forecasting services for spend analysis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, Mapping, Optional, Sequence

try:  # pragma: no cover - optional dependency guard
    import numpy as np
except ImportError:  # pragma: no cover - provide fallback behaviour
    np = None  # type: ignore
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

try:  # pragma: no cover - optional dependency
    from prophet import Prophet
except ImportError:  # pragma: no cover - fallback path tested separately
    Prophet = None  # type: ignore


@dataclass(frozen=True)
class ForecastPoint:
    """Single forecast entry."""

    ds: datetime
    yhat: float
    yhat_lower: float
    yhat_upper: float

    def to_dict(self) -> Dict[str, float | str]:
        return {
            "ds": self.ds.isoformat(),
            "yhat": self.yhat,
            "yhat_lower": self.yhat_lower,
            "yhat_upper": self.yhat_upper,
        }


@dataclass(frozen=True)
class ForecastResult:
    """Aggregate forecast output with diagnostics."""

    scope: str | None
    horizon: int
    method: str
    mape: float | None
    points: Sequence[ForecastPoint]

    def to_dict(self) -> Dict[str, object]:
        return {
            "scope": self.scope,
            "horizon": self.horizon,
            "method": self.method,
            "mape": self.mape,
            "points": [point.to_dict() for point in self.points],
        }


def _prepare_series(
    records: Iterable[Mapping[str, object]], scope: str | None
) -> pd.Series:
    frame = pd.DataFrame(list(records))
    if frame.empty:
        return pd.Series(dtype=float)

    if "date" in frame.columns:
        frame["ds"] = pd.to_datetime(frame["date"], utc=False)
    elif "ts" in frame.columns:
        frame["ds"] = pd.to_datetime(frame["ts"], utc=False)
    else:
        raise ValueError("records must contain a 'date' or 'ts' field")

    if scope is not None and "account" in frame.columns:
        frame = frame[frame["account"] == scope]

    grouped = frame.groupby("ds", as_index=True)["cost_usd"].sum().sort_index()
    if grouped.empty:
        return grouped
    full_index = pd.date_range(grouped.index.min(), grouped.index.max(), freq="D")
    grouped = grouped.reindex(full_index)
    grouped = grouped.ffill().bfill()
    return grouped.astype(float)


def _compute_mape(actual: pd.Series, predicted: pd.Series) -> float:
    if np is None:
        actual_vals = [float(value) for value in actual]
        predicted_vals = [float(value) for value in predicted]
        if not actual_vals:
            return 0.0
        denom = [max(value, 1e-6) for value in actual_vals]
        total = sum(
            abs(a - b) / d for a, b, d in zip(actual_vals, predicted_vals, denom)
        )
        return float(total / len(actual_vals) * 100.0)

    denom = np.maximum(actual.to_numpy(), 1e-6)
    return float(
        np.mean(np.abs((actual.to_numpy() - predicted.to_numpy()) / denom)) * 100.0
    )


def _detect_seasonality(series: pd.Series, default: int, horizon: int) -> int:
    """Select a seasonal period that minimises back-test error."""

    best_period = default
    best_score = float("inf")
    candidates = sorted({default, 7, 14, 30})
    for period in candidates:
        if len(series) <= period * 2:
            continue
        score = _backtest(series, horizon, period, "ets")
        if score is None:
            continue
        if score < best_score:
            best_score = score
            best_period = period
    return best_period


def _backtest(
    series: pd.Series, horizon: int, seasonal_periods: int, method: str
) -> Optional[float]:
    if len(series) <= seasonal_periods * 2:
        return None
    split = min(max(horizon, 7), len(series) // 3)
    train = series.iloc[:-split]
    test = series.iloc[-split:]
    forecast = _run_model(train, split, seasonal_periods, method)
    aligned = forecast[: len(test)]
    return _compute_mape(test, aligned)


def _run_model(
    series: pd.Series, horizon: int, seasonal_periods: int, method: str
) -> pd.Series:
    if method == "prophet":
        if Prophet is None:
            raise RuntimeError("Prophet is not installed")
        frame = pd.DataFrame({"ds": series.index, "y": series.values})
        model = Prophet(
            yearly_seasonality=False,
            weekly_seasonality=True,
            daily_seasonality=False,
        )
        model.fit(frame)
        future = model.make_future_dataframe(periods=horizon, freq="D")
        forecast = model.predict(future).tail(horizon)
        return forecast.set_index("ds")["yhat"]

    model = ExponentialSmoothing(
        series,
        trend="add",
        seasonal="add",
        seasonal_periods=seasonal_periods,
    )
    fitted = model.fit(optimized=True)
    forecast = fitted.forecast(horizon)
    return forecast


def generate_forecast(
    records: Sequence[Mapping[str, object]],
    *,
    scope: str | None = None,
    horizon: int = 90,
    method: str = "auto",
    seasonal_periods: int = 7,
) -> ForecastResult:
    """Generate forecasts for the provided spend records."""

    if horizon <= 0:
        raise ValueError("horizon must be positive")

    series = _prepare_series(records, scope)
    if series.empty:
        return ForecastResult(
            scope=scope, horizon=horizon, method=method, mape=None, points=[]
        )

    chosen_method = method
    if method == "auto":
        chosen_method = (
            "prophet" if Prophet is not None and len(series) >= 60 else "ets"
        )
    elif method == "ets":
        chosen_method = "ets"

    if chosen_method == "ets":
        seasonal_periods = _detect_seasonality(series, seasonal_periods, horizon)

    try:
        forecast_values = _run_model(series, horizon, seasonal_periods, chosen_method)
    except RuntimeError:
        chosen_method = "ets"
        forecast_values = _run_model(series, horizon, seasonal_periods, chosen_method)

    resid_std = float(series.diff().dropna().std()) if len(series) > 1 else 0.0
    interval = 1.96 * resid_std if resid_std > 0 else 0.0

    points = [
        ForecastPoint(
            ds=timestamp.to_pydatetime(),
            yhat=float(value),
            yhat_lower=float(max(value - interval, 0.0)),
            yhat_upper=float(value + interval),
        )
        for timestamp, value in forecast_values.items()
    ]

    mape = _backtest(series, horizon, seasonal_periods, chosen_method)
    return ForecastResult(
        scope=scope, horizon=horizon, method=chosen_method, mape=mape, points=points
    )


__all__ = [
    "ForecastResult",
    "ForecastPoint",
    "generate_forecast",
]
