"""Async scheduler that executes platform jobs on cadence."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Awaitable, Callable, List

from ..config import get_settings
from ..telemetry.metrics import increment_counter
from . import jobs
from .health import record_failure, record_success

JobCallable = Callable[[], None]


@dataclass
class JobSpec:
    """Describe an orchestrated job."""

    name: str
    interval: timedelta
    func: JobCallable
    last_run: datetime | None = None
    running: bool = field(default=False, init=False)

    def due(self, now: datetime) -> bool:
        if self.running:
            return False
        if self.last_run is None:
            return True
        return now - self.last_run >= self.interval


class OrchestratorAgent:
    """Manage execution of ingestion, analytics, and valuation jobs."""

    def __init__(self) -> None:
        settings = get_settings()
        fifteen_minutes = timedelta(minutes=15)
        one_day = timedelta(days=1)
        self._jobs: List[JobSpec] = [
            JobSpec("ingest", fifteen_minutes, jobs.run_ingest),
            JobSpec("anomalies", fifteen_minutes, jobs.run_anomalies),
            JobSpec("rightsizing", one_day, jobs.run_rightsizing),
            JobSpec("forecasting", one_day, jobs.run_forecasting),
            JobSpec("valuation", one_day, jobs.run_valuation),
        ]
        self._sleep_seconds = getattr(settings, "scheduler_sleep_seconds", 60)
        self._shutdown = asyncio.Event()

    async def start(self) -> None:
        """Run the scheduler loop until ``stop`` is called."""

        while not self._shutdown.is_set():
            now = datetime.utcnow()
            tasks: list[Awaitable[None]] = []
            for job in self._jobs:
                if job.due(now):
                    tasks.append(self._spawn(job))
            if tasks:
                await asyncio.gather(*tasks)
            try:
                await asyncio.wait_for(
                    self._shutdown.wait(), timeout=self._sleep_seconds
                )
            except asyncio.TimeoutError:
                continue

    def stop(self) -> None:
        """Request scheduler shutdown."""

        self._shutdown.set()

    async def _spawn(self, spec: JobSpec) -> None:
        spec.running = True
        try:
            await asyncio.to_thread(self._execute, spec)
        finally:
            spec.running = False

    def _execute(self, spec: JobSpec) -> None:
        try:
            spec.func()
        except Exception as exc:  # pragma: no cover - defensive fallback
            record_failure(spec.name, exc)
        else:
            spec.last_run = datetime.utcnow()
            record_success(spec.name, spec.last_run)
            increment_counter(f"scheduler.executed.{spec.name}")


__all__ = ["OrchestratorAgent", "JobSpec"]
