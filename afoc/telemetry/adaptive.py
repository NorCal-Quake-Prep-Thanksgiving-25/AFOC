"""Adaptive control helpers for reinforcement-style tuning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from .store import TelemetryStore


@dataclass
class AdaptiveController:
    """Derives lightweight tuning hints from telemetry history."""

    store: TelemetryStore
    lookback_days: int = 30

    def forecast_parameters(
        self, default_method: str, default_seasonal: int
    ) -> Tuple[str, int]:
        """Return tuned forecast parameters based on recent MAPE."""

        average_mape = self.store.average_metric(
            "forecast", "mape", days=self.lookback_days
        )
        method = default_method
        seasonal = default_seasonal
        if average_mape is not None:
            if average_mape > 25:
                method = "prophet"
                seasonal = max(default_seasonal, 14)
            elif average_mape < 10:
                seasonal = max(3, default_seasonal // 2 or 3)
        return method, seasonal

    def rightsizing_headroom(self, default_headroom: float) -> float:
        """Adjust headroom based on realised savings."""

        average_savings = self.store.average_metric(
            "rightsizing", "savings_ratio", days=self.lookback_days
        )
        if average_savings is None:
            return default_headroom
        if average_savings < 0.05:
            return min(default_headroom * 1.25, 0.4)
        if average_savings > 0.3:
            return max(default_headroom * 0.8, 0.05)
        return default_headroom

    def valuation_multiplier(self, default_multiplier: float) -> float:
        """Scale valuation multiplier based on integrated returns."""

        avg_integrated = self.store.average_metric(
            "valuation", "integrated_value", days=self.lookback_days
        )
        if avg_integrated is None:
            return default_multiplier
        if avg_integrated > 250000:
            return default_multiplier * 1.1
        if avg_integrated < 50000:
            return default_multiplier * 0.9
        return default_multiplier

    def register_forecast(self, mape: float | None) -> None:
        if mape is None:
            return
        self.store.record_event(
            "forecast_metric", metadata={"mape": mape}, after_value=mape
        )


__all__ = ["AdaptiveController"]
