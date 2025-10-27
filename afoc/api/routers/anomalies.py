"""Anomaly API routes."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

if TYPE_CHECKING:  # pragma: no cover - only for type checking
    from ...services.anomalies import Anomaly

from ...telemetry import TelemetryStore
from ..security import enforce_security

router = APIRouter(dependencies=[Depends(enforce_security)])


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

    records = [record.model_dump() for record in payload]
    try:
        from ...services import anomalies as anomaly_service
    except ImportError as exc:  # pragma: no cover - triggered when deps missing
        raise HTTPException(
            status_code=503, detail="anomaly service unavailable"
        ) from exc

    detected = anomaly_service.detect_anomalies(records)
    responses = _render_response(detected)
    store = TelemetryStore.default()
    for item, response in zip(detected, responses):
        scope_str = "/".join(filter(None, item.scope))
        store.record_event(
            "anomaly",
            scope=scope_str or None,
            before_value=item.expected,
            after_value=item.observed,
            metadata={
                "score": item.score,
                "method": item.method,
                "payload": response.model_dump(),
            },
        )
    return responses
