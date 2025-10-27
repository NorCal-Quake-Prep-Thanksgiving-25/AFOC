"""ROI proof endpoint."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from io import StringIO
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ...db import session_scope
from ...db.models import TelemetryEventRecord, ValueProof
from ...services import valuation
from ...telemetry.events import Severity, ValuationEvent
from ...telemetry.bus import publish
from ..security import enforce_security

router = APIRouter(dependencies=[Depends(enforce_security)])


class ProofResponse(BaseModel):
    json: Dict[str, object]
    markdown: str
    csv: str


def _period_bounds(period: str) -> tuple[date, date]:
    today = datetime.utcnow().date()
    if period == "last_30d":
        return today - timedelta(days=30), today
    if period == "last_60d":
        return today - timedelta(days=60), today
    if period == "last_90d":
        return today - timedelta(days=90), today
    raise HTTPException(status_code=400, detail="unsupported period")


def _load_payloads(event_type: str, start: date, end: date) -> list[dict]:
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end, datetime.max.time())
    from sqlalchemy import select

    with session_scope() as session:
        rows = (
            session.execute(
                select(TelemetryEventRecord)
                .where(TelemetryEventRecord.event_type == event_type)
                .where(TelemetryEventRecord.ts >= start_dt)
                .where(TelemetryEventRecord.ts <= end_dt)
            )
            .scalars()
            .all()
        )
    return [row.payload or {} for row in rows]


def _to_float(value: Any) -> float:
    """Coerce heterogeneous payload values into a float safely."""

    if isinstance(value, Decimal):  # pragma: no cover - defensive guard
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        candidate = value.strip().replace("$", "").replace(",", "")
        try:
            return float(candidate)
        except ValueError:
            return 0.0
    return 0.0


def _render_markdown(payload: Dict[str, float], assumptions: Dict[str, object]) -> str:
    lines = ["# ROI Proof", "", "| Component | Value (USD) |", "|---|---|"]
    for key in ("anomaly", "rightsize", "forecast", "integrated"):
        lines.append(f"| {key} | ${payload[key]:,.2f} |")
    lines.append("")
    lines.append("## Assumptions")
    for key, value in assumptions.items():
        lines.append(f"- **{key}**: {value}")
    return "\n".join(lines)


def _render_csv(payload: Dict[str, float]) -> str:
    buffer = StringIO()
    buffer.write("component,value\n")
    for key in ("anomaly", "rightsize", "forecast", "integrated"):
        buffer.write(f"{key},{payload[key]:.2f}\n")
    return buffer.getvalue()


@router.get("", response_model=ProofResponse)
def generate_proof(
    tier: str = Query("mid"),
    annual_spend: float = Query(1_000_000, gt=0),
    period: str = Query("last_30d"),
) -> ProofResponse:
    start, end = _period_bounds(period)
    anomalies = _load_payloads("anomaly", start, end)
    rightsizing = _load_payloads("rightsize", start, end)
    forecasts = _load_payloads("forecast", start, end)

    total_anomaly = sum(_to_float(item.get("observed", 0.0)) for item in anomalies)
    monthly_savings = sum(_to_float(item.get("savings", 0.0)) for item in rightsizing)
    reservable = 0.0
    for item in forecasts:
        points = item.get("points")
        if not isinstance(points, list):
            continue
        for point in points:
            if isinstance(point, dict):
                reservable += _to_float(point.get("yhat", 0.0))

    inputs = valuation.ValueInputs(
        annual_spend=annual_spend,
        anomaly_spend=total_anomaly,
        rightsizing_monthly_savings=monthly_savings,
        reservable_spend=reservable,
        tier=tier,
        anomaly_count=len(anomalies),
    )
    report = valuation.compute_value_report(inputs)

    payload = {
        "anomaly": report.anomaly,
        "rightsize": report.rightsize,
        "forecast": report.forecast,
        "integrated": report.integrated,
    }

    publish(
        ValuationEvent(
            scope="proof",
            severity=Severity.INFO,
            payload={"tier": tier, **payload, "period": period},
            dedupe_key=f"proof:{tier}:{period}:{annual_spend}",
        )
    )

    with session_scope() as session:
        proof = ValueProof(
            period_start=start,
            period_end=end,
            tier=tier,
            annual_spend=annual_spend,
            anomaly_value=report.anomaly,
            rightsize_value=report.rightsize,
            forecast_value=report.forecast,
            integrated_value=report.integrated,
            assumptions=report.assumptions,
        )
        session.add(proof)

    markdown = _render_markdown(payload, report.assumptions)
    csv = _render_csv(payload)
    return ProofResponse(
        json={"payload": payload, "assumptions": report.assumptions},
        markdown=markdown,
        csv=csv,
    )


__all__ = ["router"]
