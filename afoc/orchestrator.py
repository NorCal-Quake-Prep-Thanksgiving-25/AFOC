"""Autonomous orchestration agent that keeps the platform up to date."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .db.models import ResourceInventory, UsageEvent
from .services import anomalies as anomaly_service
from .services import forecasting as forecasting_service
from .services import rightsizing as rightsizing_service
from .services import valuation as valuation_service
from .telemetry import AdaptiveController, TelemetryEvent, TelemetryStore


class Agent:
    """Runs scheduled analytics pipelines and records telemetry."""

    def __init__(self, *, telemetry: TelemetryStore | None = None) -> None:
        self.settings = get_settings()
        self.telemetry = telemetry or TelemetryStore.default()
        from sqlalchemy import create_engine

        self._engine = create_engine(self.settings.database_url, future=True)
        self._adaptive = AdaptiveController(self.telemetry)

    def _usage_records(self, days: int) -> List[dict]:
        cutoff = datetime.utcnow() - timedelta(days=days)
        with Session(self._engine) as session:
            rows = session.execute(
                select(UsageEvent).where(UsageEvent.occurred_at >= cutoff)
            ).scalars()
            return [
                {
                    "ts": row.occurred_at,
                    "provider": (
                        row.metadata.get("provider", row.source)
                        if row.metadata
                        else row.source
                    ),
                    "account": row.metadata.get("account") if row.metadata else None,
                    "service": row.service,
                    "cost_usd": float(row.cost),
                }
                for row in rows
            ]

    def _inventory_payload(
        self,
    ) -> tuple[List[Mapping[str, object]], List[Mapping[str, object]]]:
        with Session(self._engine) as session:
            resources = session.execute(select(ResourceInventory)).scalars().all()
        inventory: List[Mapping[str, object]] = []
        utilization: List[Mapping[str, object]] = []
        for resource in resources:
            metadata = resource.metadata or {}
            inventory.append(
                {
                    "resource_id": resource.resource_id,
                    "instance_type": metadata.get(
                        "instance_type", resource.resource_type
                    ),
                    "price": metadata.get("price", 0.0),
                    "cpu_capacity": metadata.get("cpu_capacity", 1.0),
                    "memory_capacity": metadata.get("memory_capacity", 1.0),
                    "metadata": metadata,
                }
            )
            utilization.append(
                {
                    "resource_id": resource.resource_id,
                    "p95_cpu": metadata.get("p95_cpu"),
                    "p95_mem": metadata.get("p95_mem"),
                }
            )
        return inventory, utilization

    def run_daily(self, *, horizon: int = 60) -> None:
        """Execute the daily analytics pipeline and record telemetry."""

        usage_records = self._usage_records(days=90)
        if usage_records:
            detected = anomaly_service.detect_anomalies(usage_records)
            events = [
                TelemetryEvent(
                    recorded_at=item.ts,
                    event_type="anomaly",
                    scope="/".join(filter(None, item.scope)),
                    before_value=item.expected,
                    after_value=item.observed,
                    delta_value=item.observed - item.expected,
                    metadata={"score": item.score, "method": item.method},
                )
                for item in detected
            ]
            self.telemetry.record_events(events)

        inventory, utilization = self._inventory_payload()
        if inventory and utilization:
            headroom = self._adaptive.rightsizing_headroom(0.15)
            recommendations = rightsizing_service.generate_recommendations(
                inventory, utilization, headroom=headroom
            )
            for rec in recommendations:
                before = float(rec["current_price"])
                after = float(rec["recommended_price"])
                savings = max(before - after, 0.0)
                metadata = {
                    **rec,
                    "savings_ratio": (savings / before) if before else 0.0,
                }
                self.telemetry.record_event(
                    "rightsizing",
                    scope=str(rec["resource_id"]),
                    before_value=before,
                    after_value=after,
                    metadata=metadata,
                )

        scope = None
        method, seasonal = self._adaptive.forecast_parameters("auto", 7)
        forecast_input = [
            {
                "date": record["ts"],
                "cost_usd": record["cost_usd"],
                "account": record.get("account"),
            }
            for record in usage_records
        ]
        if forecast_input:
            forecast = forecasting_service.generate_forecast(
                forecast_input,
                scope=scope,
                horizon=horizon,
                method=method,
                seasonal_periods=seasonal,
            )
            first_point = forecast.points[0] if forecast.points else None
            baseline = forecast_input[-1]["cost_usd"] if forecast_input else None
            self.telemetry.record_event(
                "forecast",
                scope=scope,
                before_value=float(baseline) if baseline is not None else None,
                after_value=float(first_point.yhat) if first_point else None,
                metadata={
                    "method": forecast.method,
                    "horizon": forecast.horizon,
                    "mape": forecast.mape,
                },
            )

        summary = self.telemetry.summarise(days=90)
        overall_delta = float(summary["overall"].get("delta", 0.0))
        overall_after = float(summary["overall"].get("after", 0.0))
        anomaly_totals = summary["totals"].get("anomaly", {})
        valuation_inputs = valuation_service.ValueInputs(
            annual_spend=(overall_after * 12 / 90) if usage_records else 0.0,
            anomaly_spend=float(anomaly_totals.get("after", 0.0)),
            rightsizing_monthly_savings=max(overall_delta, 0.0) / 12,
            reservable_spend=overall_after * 0.3,
            tier="mid",
            anomaly_count=int(anomaly_totals.get("count", 0.0)),
        )
        report = valuation_service.compute_value_report(valuation_inputs)
        multiplier = self._adaptive.valuation_multiplier(1.0)
        adjusted_value = report.integrated * multiplier
        self.telemetry.record_event(
            "valuation",
            scope="enterprise",
            before_value=0.0,
            after_value=adjusted_value,
            metadata={
                "anomaly": report.anomaly,
                "rightsize": report.rightsize,
                "forecast": report.forecast,
                "integrated_value": adjusted_value,
                "multiplier": multiplier,
            },
        )


__all__ = ["Agent"]
