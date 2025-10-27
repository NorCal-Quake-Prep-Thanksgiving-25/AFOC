"""Health reporting for the orchestrator."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict

from sqlalchemy import func, select

from ..db import session_scope
from ..db.models import TelemetryEventRecord


@dataclass
class JobHealth:
    """Track success and failure timestamps for a job."""

    last_success: datetime | None = None
    last_error: datetime | None = None
    error: str | None = None


_STATE: Dict[str, JobHealth] = defaultdict(JobHealth)


def record_success(name: str, when: datetime | None = None) -> None:
    state = _STATE[name]
    state.last_success = when or datetime.utcnow()
    state.error = None


def record_failure(name: str, exc: Exception) -> None:
    state = _STATE[name]
    state.last_error = datetime.utcnow()
    state.error = str(exc)


def readiness() -> Dict[str, object]:
    """Return readiness information including DB connectivity and queue lag."""

    try:
        with session_scope() as session:
            pending = (
                session.execute(
                    select(func.count()).select_from(
                        select(TelemetryEventRecord)
                        .where(TelemetryEventRecord.processed.is_(False))
                        .subquery()
                    )
                )
                .scalars()
                .one()
            )
    except Exception as exc:  # pragma: no cover - defensive fallback
        return {"ready": False, "error": str(exc)}

    stale_jobs = {
        name: health
        for name, health in _STATE.items()
        if health.last_success is None
        or datetime.utcnow() - health.last_success > timedelta(hours=6)
    }
    return {
        "ready": not stale_jobs,
        "pending_events": int(pending),
        "stale_jobs": {name: health.__dict__ for name, health in stale_jobs.items()},
    }


def liveness() -> Dict[str, object]:
    """Expose liveness status for probes."""

    return {
        "alive": True,
        "jobs": {name: health.__dict__ for name, health in _STATE.items()},
    }


__all__ = ["record_success", "record_failure", "readiness", "liveness"]
