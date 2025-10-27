"""Reporting API routes."""

from __future__ import annotations

from typing import Dict, List, cast

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from ...services import aggregator, valuation
from ...telemetry.bus import publish
from ...telemetry.events import Severity, ValuationEvent
from ..security import enforce_security

router = APIRouter(dependencies=[Depends(enforce_security)])


@router.post("/")
def generate(payload: Dict[str, object]) -> Dict[str, object]:
    """Return a combined report."""

    anomalies = cast(List[dict], payload.get("anomalies", []))
    forecast = cast(List[float], payload.get("forecast", []))
    return aggregator.build_report(anomalies, forecast)


class ValueQuery(BaseModel):
    """Query parameters for the valuation endpoint."""

    tier: str = "mid"
    annual_spend: float = Query(..., gt=0)
    anomaly_spend: float = 0.0
    rightsizing_monthly_savings: float = 0.0
    reservable_spend: float = 0.0
    anomaly_count: int = 0


@router.get("/value")
def value_report(params: ValueQuery = Depends()) -> Dict[str, object]:
    """Return the valuation breakdown for the given tier and spend."""

    inputs = valuation.ValueInputs(
        annual_spend=params.annual_spend,
        anomaly_spend=params.anomaly_spend,
        rightsizing_monthly_savings=params.rightsizing_monthly_savings,
        reservable_spend=params.reservable_spend,
        tier=params.tier,
        anomaly_count=params.anomaly_count,
    )
    report = valuation.compute_value_report(inputs)
    publish(
        ValuationEvent(
            scope=params.tier,
            severity=Severity.INFO,
            payload={
                "anomaly": report.anomaly,
                "rightsize": report.rightsize,
                "forecast": report.forecast,
                "integrated_value": report.integrated,
            },
            dedupe_key=f"valuation:{params.tier}:{inputs.annual_spend}",
        )
    )
    return report.to_dict()


@router.get("/proof")
def proof(window_days: int = Query(90, ge=7, le=365)) -> Dict[str, object]:
    """Return an ROI proof payload summarising before/after outcomes."""

    return aggregator.proof(window_days)
