"""Reliability primitives for orchestration and provider resilience."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any, Callable, Dict, Optional, Protocol


class CircuitBreakerOpen(RuntimeError):
    """Raised when a circuit breaker rejects a call."""


class CircuitBreaker:
    """Simple circuit breaker supporting half-open recovery."""

    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        on_state_change: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.failure_threshold = max(1, failure_threshold)
        self.recovery_timeout = max(1.0, recovery_timeout)
        self._on_state_change = on_state_change
        self._state = "closed"
        self._failure_count = 0
        self._opened_at: float | None = None
        self._lock = Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def call(self, func: Callable[[], Any]) -> Any:
        with self._lock:
            if self._state == "open":
                if (
                    self._opened_at is not None
                    and (time.time() - self._opened_at) >= self.recovery_timeout
                ):
                    self._transition("half-open")
                else:
                    raise CircuitBreakerOpen("circuit breaker open")

        try:
            result = func()
        except Exception:
            self.record_failure()
            raise
        self.record_success()
        return result

    def record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            if self._failure_count >= self.failure_threshold:
                self._transition("open")

    def record_success(self) -> None:
        with self._lock:
            self._failure_count = 0
            if self._state != "closed":
                self._transition("closed")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _transition(self, state: str) -> None:
        self._state = state
        if state == "open":
            self._opened_at = time.time()
        else:
            self._opened_at = None
        if self._on_state_change:
            self._on_state_change(state)

    @property
    def state(self) -> str:
        return self._state


# ---------------------------------------------------------------------------
# Persistent job queue
# ---------------------------------------------------------------------------


class SupportsJobStorage(Protocol):
    """Protocol satisfied by storage backends that can persist jobs."""

    def persist_job(self, job: "JobRecord") -> None: ...

    def fetch_job(self, *, tenant_id: str, job_id: str) -> Optional["JobRecord"]: ...

    def lease_next_job(
        self,
        *,
        tenant_id: str,
        now: datetime,
        worker_id: str,
        visibility_timeout: int,
    ) -> Optional["JobRecord"]: ...

    def update_job(self, job: "JobRecord") -> None: ...

    def append_audit(self, tenant_id: str, action: str, payload: Dict[str, Any]) -> None: ...


@dataclass
class JobRecord:
    """Represents a queued job."""

    job_id: str
    tenant_id: str
    payload: Dict[str, Any]
    status: str = "pending"
    attempts: int = 0
    last_error: str | None = None
    scheduled_at: datetime = datetime.now(timezone.utc)
    available_at: datetime = datetime.now(timezone.utc)
    worker_id: str | None = None

    def to_json(self) -> str:
        return json.dumps(
            {
                "job_id": self.job_id,
                "tenant_id": self.tenant_id,
                "payload": self.payload,
                "status": self.status,
                "attempts": self.attempts,
                "last_error": self.last_error,
                "scheduled_at": self.scheduled_at.isoformat(),
                "available_at": self.available_at.isoformat(),
                "worker_id": self.worker_id,
            }
        )


class JobQueue:
    """Durable job queue with retry and idempotency controls."""

    def __init__(self, storage: SupportsJobStorage) -> None:
        self._storage = storage

    def enqueue(
        self,
        *,
        tenant_id: str,
        job_id: str,
        payload: Dict[str, Any],
        schedule_at: Optional[datetime] = None,
    ) -> JobRecord:
        schedule_at = schedule_at or datetime.now(timezone.utc)
        existing = self._storage.fetch_job(tenant_id=tenant_id, job_id=job_id)
        if existing and existing.status in {"pending", "processing", "completed"}:
            return existing
        record = JobRecord(
            job_id=job_id,
            tenant_id=tenant_id,
            payload=payload,
            status="pending",
            attempts=existing.attempts if existing else 0,
            last_error=None,
            scheduled_at=schedule_at,
            available_at=schedule_at,
        )
        self._storage.persist_job(record)
        self._storage.append_audit(
            tenant_id,
            "job.enqueued",
            {"job_id": job_id, "payload": payload, "scheduled_at": schedule_at.isoformat()},
        )
        return record

    def lease(
        self,
        *,
        tenant_id: str,
        worker_id: str,
        visibility_timeout: int = 60,
    ) -> Optional[JobRecord]:
        now = datetime.now(timezone.utc)
        job = self._storage.lease_next_job(
            tenant_id=tenant_id,
            now=now,
            worker_id=worker_id,
            visibility_timeout=visibility_timeout,
        )
        if job:
            self._storage.append_audit(
                tenant_id,
                "job.leased",
                {"job_id": job.job_id, "worker_id": worker_id, "attempts": job.attempts},
            )
        return job

    def complete(self, job: JobRecord) -> None:
        job.status = "completed"
        job.available_at = datetime.now(timezone.utc)
        job.worker_id = None
        self._storage.update_job(job)
        self._storage.append_audit(
            job.tenant_id,
            "job.completed",
            {"job_id": job.job_id, "attempts": job.attempts},
        )

    def fail(self, job: JobRecord, *, error: str, retry_delay: int = 60) -> None:
        job.status = "pending"
        job.last_error = error
        job.available_at = datetime.now(timezone.utc) + timedelta(seconds=retry_delay)
        self._storage.update_job(job)
        self._storage.append_audit(
            job.tenant_id,
            "job.failed",
            {"job_id": job.job_id, "error": error, "attempts": job.attempts},
        )
