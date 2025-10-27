"""Concrete orchestration jobs for the AFOC platform."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from time import perf_counter
from typing import List, Mapping

from sqlalchemy import select

from ..config import get_settings
from ..db import session_scope
from ..db.models import (
    ResourceInventory,
    TelemetryEventRecord,
    UsageEvent,
    Utilization,
    ValueProof,
)
from ..ingest import loaders
from ..learning import apply_policy_updates, build_snapshot
from ..services import anomalies as anomaly_service
from ..services import forecasting as forecasting_service
from ..services import rightsizing as rightsizing_service
from ..services import valuation as valuation_service
from ..telemetry.bus import publish, publish_many
from ..telemetry.events import (
    AnomalyEvent,
    ErrorEvent,
    ForecastEvent,
    RightsizeEvent,
    Severity,
    ValuationEvent,
)
from ..telemetry.metrics import increment_counter, observe_latency

_LOGGER = logging.getLogger(__name__)
_SAMPLE_DIR = Path(__file__).resolve().parents[1] / "sample_data"


def _to_float(value: object) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def run_ingest() -> None:
    """Load available sample datasets and persist them to the database."""

    start = perf_counter()
    settings = get_settings()
    ingested = 0
    datasets: List[Path] = []
    for filename in ("openai_usage_sample.csv", "aws_cur_sample.csv"):
        candidate = _SAMPLE_DIR / filename
        if candidate.exists():
            datasets.append(candidate)
    for dataset in datasets:
        try:
            frame = _load_dataset(dataset)
            ingested += frame.height
        except Exception as exc:  # pragma: no cover - defensive path
            _LOGGER.exception("Failed to ingest %s", dataset, exc_info=exc)
            publish(
                ErrorEvent(
                    scope=str(dataset),
                    payload={"error": str(exc)},
                    dedupe_key=f"ingest:error:{dataset}",
                )
            )
    duration = perf_counter() - start
    observe_latency("jobs.ingest", duration)
    publish(
        ValuationEvent(
            scope="ingest",
            severity=Severity.INFO,
            payload={
                "datasets": [str(path) for path in datasets],
                "rows_ingested": ingested,
                "database_url": settings.database_url,
            },
            dedupe_key=f"ingest:{date.today().isoformat()}",
        )
    )
    increment_counter("jobs.ingest")


def run_anomalies() -> None:
    """Execute anomaly detection and emit telemetry events."""

    start = perf_counter()
    records = _usage_records(days=90)
    anomalies = anomaly_service.detect_anomalies(records)
    events = [
        AnomalyEvent(
            scope="/".join(filter(None, anomaly.scope)),
            severity=Severity.WARN,
            payload={
                "ts": anomaly.ts.isoformat(),
                "observed": anomaly.observed,
                "expected": anomaly.expected,
                "score": anomaly.score,
                "method": anomaly.method,
            },
            dedupe_key=f"anomaly:{'/'.join(filter(None, anomaly.scope))}:{anomaly.ts.date()}",
        )
        for anomaly in anomalies
    ]
    publish_many(events)
    observe_latency("jobs.anomalies", perf_counter() - start)
    increment_counter("jobs.anomalies")


def run_rightsizing(headroom: float | None = None, policy: str = "cost") -> None:
    """Generate right-sizing recommendations and emit telemetry."""

    start = perf_counter()
    inventory, utilisation = _inventory_payloads()
    if not inventory or not utilisation:
        return
    effective_headroom = headroom if headroom is not None else 0.15
    recommendations = rightsizing_service.generate_recommendations(
        inventory,
        utilisation,
        headroom=effective_headroom,
        policy=policy,
    )
    events = []
    for rec in recommendations:
        current_price = _to_float(rec.get("current_price", 0.0))
        recommended_price = _to_float(rec.get("recommended_price", current_price))
        savings = max(current_price - recommended_price, 0.0)
        ratio = (savings / current_price) if current_price else 0.0
        events.append(
            RightsizeEvent(
                scope=str(rec["resource_id"]),
                severity=Severity.INFO,
                payload={
                    "savings": savings,
                    "savings_ratio": ratio,
                    **rec,
                },
                dedupe_key=f"rightsize:{rec['resource_id']}:{date.today().isoformat()}",
            )
        )
    publish_many(events)
    observe_latency("jobs.rightsizing", perf_counter() - start)
    increment_counter("jobs.rightsizing")


def run_forecasting(scope: str | None = None, horizon: int = 90) -> None:
    """Generate forecasts for spend and publish telemetry."""

    start = perf_counter()
    records = _usage_records(days=180)
    forecast = forecasting_service.generate_forecast(
        records, scope=scope, horizon=horizon
    )
    payload = {
        "method": forecast.method,
        "horizon": forecast.horizon,
        "mape": forecast.mape,
        "points": [point.to_dict() for point in forecast.points[:10]],
    }
    publish(
        ForecastEvent(
            scope=scope or "global",
            severity=Severity.INFO,
            payload=payload,
            dedupe_key=f"forecast:{scope or 'global'}:{horizon}:{date.today().isoformat()}",
        )
    )
    observe_latency("jobs.forecasting", perf_counter() - start)
    increment_counter("jobs.forecasting")


def run_valuation(tier: str = "mid", annual_spend: float | None = None) -> None:
    """Aggregate telemetry and persist a valuation proof."""

    start = perf_counter()
    cutoff = datetime.utcnow() - timedelta(days=30)
    anomaly_payloads = _recent_payloads("anomaly", cutoff)
    rightsize_payloads = _recent_payloads("rightsize", cutoff)
    forecast_payloads = _recent_payloads("forecast", cutoff)

    total_anomaly = sum(
        _to_float(item.get("observed", 0.0)) for item in anomaly_payloads
    )
    monthly_savings = sum(
        _to_float(item.get("savings", 0.0)) for item in rightsize_payloads
    )
    reservable = 0.0
    for item in forecast_payloads:
        points = item.get("points")
        if isinstance(points, list):
            for point in points:
                if isinstance(point, dict):
                    reservable += _to_float(point.get("yhat", 0.0))
    spend = annual_spend if annual_spend is not None else max(total_anomaly * 12, 0.0)

    inputs = valuation_service.ValueInputs(
        annual_spend=spend,
        anomaly_spend=total_anomaly,
        rightsizing_monthly_savings=monthly_savings,
        reservable_spend=reservable,
        tier=tier,
        anomaly_count=len(anomaly_payloads),
    )
    report = valuation_service.compute_value_report(inputs)

    publish(
        ValuationEvent(
            scope="valuation",
            severity=Severity.INFO,
            payload={"report": report.to_dict(), "tier": tier},
            dedupe_key=f"valuation:{tier}:{date.today().isoformat()}",
        )
    )

    with session_scope() as session:
        proof = ValueProof(
            period_start=(datetime.utcnow() - timedelta(days=30)).date(),
            period_end=datetime.utcnow().date(),
            tier=tier,
            annual_spend=spend,
            anomaly_value=report.anomaly,
            rightsize_value=report.rightsize,
            forecast_value=report.forecast,
            integrated_value=report.integrated,
            assumptions=report.assumptions,
        )
        session.add(proof)

    snapshot = build_snapshot(
        rightsizing=rightsize_payloads,
        forecasting=forecast_payloads,
        anomalies=anomaly_payloads,
    )
    apply_policy_updates(snapshot)

    observe_latency("jobs.valuation", perf_counter() - start)
    increment_counter("jobs.valuation")


def _usage_records(days: int) -> List[dict]:
    cutoff = datetime.utcnow() - timedelta(days=days)
    with session_scope() as session:
        rows = (
            session.execute(select(UsageEvent).where(UsageEvent.occurred_at >= cutoff))
            .scalars()
            .all()
        )
    records = []
    for row in rows:
        metadata = row.metadata_json or {}
        records.append(
            {
                "ts": row.occurred_at,
                "provider": metadata.get("provider", row.source),
                "account": metadata.get("account"),
                "service": row.service,
                "cost_usd": float(row.cost),
            }
        )
    return records


def _inventory_payloads() -> (
    tuple[List[Mapping[str, object]], List[Mapping[str, object]]]
):
    with session_scope() as session:
        resources = session.execute(select(ResourceInventory)).scalars().all()
        resource_map = {resource.id: resource for resource in resources}
        utilisation_rows = session.execute(select(Utilization)).scalars().all()

    inventory: List[Mapping[str, object]] = []
    utilisation_records: List[Mapping[str, object]] = []
    for resource in resources:
        metadata = resource.metadata_json or {}
        inventory.append(
            {
                "resource_id": resource.resource_id,
                "instance_type": metadata.get("instance_type", resource.resource_type),
                "price": float(metadata.get("price", 0.0)),
                "cpu_capacity": float(metadata.get("cpu_capacity", 1.0)),
                "memory_capacity": float(metadata.get("memory_capacity", 1.0)),
                "metadata": metadata,
            }
        )
    for entry in utilisation_rows:
        resource = resource_map.get(entry.resource_id)
        utilisation_records.append(
            {
                "resource_id": resource.resource_id if resource else None,
                "p95_cpu": entry.cpu_percent,
                "p95_mem": entry.memory_percent,
            }
        )
    return inventory, utilisation_records


def _recent_payloads(event_type: str, cutoff: datetime) -> List[Mapping[str, object]]:
    with session_scope() as session:
        rows = (
            session.execute(
                select(TelemetryEventRecord)
                .where(TelemetryEventRecord.event_type == event_type)
                .where(TelemetryEventRecord.ts >= cutoff)
            )
            .scalars()
            .all()
        )
    return [row.payload or {} for row in rows]


def _load_dataset(path: Path):
    if "openai" in path.name:
        return loaders.load_openai_usage_csv(path)
    if "aws" in path.name:
        return loaders.load_aws_cur_csv(path)
    return loaders.load_generic_usage_csv(path, mapping={})


__all__ = [
    "run_ingest",
    "run_anomalies",
    "run_rightsizing",
    "run_forecasting",
    "run_valuation",
]
