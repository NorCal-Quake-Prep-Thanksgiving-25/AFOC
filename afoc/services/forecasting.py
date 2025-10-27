"""Forecasting service stubs."""

from typing import List


def generate_forecast(series: List[float]) -> List[float]:
    """Return a placeholder forecast for the provided series."""

    return series[-3:]
