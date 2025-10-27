"""Tests for forecasting services."""

from afoc.services import forecasting


def test_generate_forecast_returns_recent_values() -> None:
    """The forecast should echo the latest observations for now."""

    result = forecasting.generate_forecast([1.0, 2.0, 3.0, 4.0])
    assert result == [2.0, 3.0, 4.0]
