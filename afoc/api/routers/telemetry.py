"""Expose telemetry events for diagnostics."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from ...db import session_scope
from ...db.models import TelemetryEventRecord
from ...telemetry.metrics import snapshot
from ..security import enforce_security

router = APIRouter(dependencies=[Depends(enforce_security)])


class TelemetryEventOut(BaseModel):
    id: int
    ts: datetime
    event_type: str
    scope: str
    severity: str
    payload: dict
    dedupe_key: Optional[str]


class TelemetryResponse(BaseModel):
    events: List[TelemetryEventOut]
    metrics: dict


@router.get("/events", response_model=TelemetryResponse)
def list_events(
    since: Optional[datetime] = Query(default=None),
    event_type: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> TelemetryResponse:
    """Return telemetry events filtered by type and time."""

    from sqlalchemy import select

    with session_scope() as session:
        stmt = (
            select(TelemetryEventRecord)
            .order_by(TelemetryEventRecord.ts.desc())
            .limit(limit)
        )
        if since is not None:
            stmt = stmt.where(TelemetryEventRecord.ts >= since)
        if event_type is not None:
            stmt = stmt.where(TelemetryEventRecord.event_type == event_type)
        rows = session.execute(stmt).scalars().all()
    events = [
        TelemetryEventOut(
            id=row.id,
            ts=row.ts,
            event_type=row.event_type,
            scope=row.scope,
            severity=row.severity,
            payload=row.payload or {},
            dedupe_key=row.dedupe_key,
        )
        for row in rows
    ]
    return TelemetryResponse(events=events, metrics=snapshot())


__all__ = ["router"]
