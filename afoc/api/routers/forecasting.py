"""Forecasting API routes."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()


class ForecastRecord(BaseModel):
    """Single spend observation."""

    date: datetime
    cost_usd: float
    account: str | None = None


class ForecastRequest(BaseModel):
    """Forecast request payload."""

    records: list[ForecastRecord]


@router.post("")
def forecast(
    payload: ForecastRequest,
    scope: str | None = Query(default=None, description="Account or business scope"),
    h: int = Query(default=90, ge=1, le=365, description="Forecast horizon in days"),
    method: str = Query(
        default="auto", description="Forecast method: auto, ets, prophet"
    ),
    seasonal_periods: int = Query(
        default=7, ge=1, le=60, description="Seasonal period length"
    ),
) -> dict:
    """Return a forecast for the provided records."""

    try:
        from ...services import forecasting as service
    except ImportError as exc:  # pragma: no cover - triggered when deps missing
        raise HTTPException(
            status_code=503, detail="forecasting service unavailable"
        ) from exc

    records = [record.model_dump() for record in payload.records]
    result = service.generate_forecast(
        records,
        scope=scope,
        horizon=h,
        method=method,
        seasonal_periods=seasonal_periods,
    )
    return result.to_dict()
