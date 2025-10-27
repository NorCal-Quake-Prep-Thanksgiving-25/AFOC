"""Anomaly API routes."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, TYPE_CHECKING

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

if TYPE_CHECKING:  # pragma: no cover - only for type checking
    from ...services.anomalies import Anomaly

router = APIRouter()


class AnomalyRequest(BaseModel):
    """Request payload describing a usage record."""

    ts: datetime
    provider: str
    account: str | None = None
    service: str
    cost_usd: float


class AnomalyScope(BaseModel):
    """Scope metadata for detected anomalies."""

    provider: str
    account: str | None
    service: str


class AnomalyResponse(BaseModel):
    """Response payload for detected anomalies."""

    ts: datetime
    scope: AnomalyScope
    observed: float
    expected: float
    score: float
    method: str


def _render_response(items: Iterable["Anomaly"]) -> List[AnomalyResponse]:
    responses: list[AnomalyResponse] = []
    for item in items:
        provider, account, service = item.scope
        responses.append(
            AnomalyResponse(
                ts=item.ts,
                scope=AnomalyScope(provider=provider, account=account, service=service),
                observed=item.observed,
                expected=item.expected,
                score=item.score,
                method=item.method,
            )
        )
    return responses


@router.post("/analyze/anomalies", response_model=List[AnomalyResponse])
def analyze_anomalies(payload: List[AnomalyRequest]) -> List[AnomalyResponse]:
    """Detect anomalies from the provided payload."""

    records = [record.dict() for record in payload]
    try:
        from ...services import anomalies as anomaly_service
    except ImportError as exc:  # pragma: no cover - triggered when deps missing
        raise HTTPException(
            status_code=503, detail="anomaly service unavailable"
        ) from exc

    return _render_response(anomaly_service.detect_anomalies(records))
