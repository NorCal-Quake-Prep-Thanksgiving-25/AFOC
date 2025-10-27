"""Tests for forecasting services."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

try:  # pragma: no cover - optional dependency guard
    import numpy as np
    import pandas as pd
    from afoc.services import forecasting
except ImportError:  # pragma: no cover - skip when scientific stack unavailable
    np = None  # type: ignore
    pd = None  # type: ignore
    forecasting = None  # type: ignore


pytestmark = pytest.mark.skipif(
    forecasting is None or np is None or pd is None,
    reason="scientific dependencies not available",
)


def _seasonal_series(days: int = 180) -> list[dict]:
    base = datetime(2024, 1, 1)
    records: list[dict] = []
    for offset in range(days):
        ts = base + timedelta(days=offset)
        seasonal = 200 + 20 * np.sin(2 * np.pi * offset / 30)
        weekly = 8 * np.sin(2 * np.pi * offset / 7)
        noise = 3 * np.cos(2 * np.pi * offset / 14)
        cost = seasonal + weekly + noise
        records.append({"date": ts, "account": "acct-a", "cost_usd": float(cost)})
    return records


def test_generate_forecast_produces_reasonable_mape() -> None:
    """ETS forecasts should achieve good accuracy on seasonal series."""

    records = _seasonal_series()
    result = forecasting.generate_forecast(
        records, scope="acct-a", horizon=30, method="ets"
    )
    assert result.points
    assert result.mape is not None
    assert result.mape < 20


def test_generate_forecast_auto_fallback() -> None:
    """Auto mode should succeed even without Prophet installed."""

    records = _seasonal_series(120)
    result = forecasting.generate_forecast(
        records, scope="acct-a", horizon=15, method="auto"
    )
    assert len(result.points) == 15
    assert result.method in {"ets", "prophet"}
