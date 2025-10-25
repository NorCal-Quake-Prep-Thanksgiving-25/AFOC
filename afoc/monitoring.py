"""Monitoring and governance utilities for the AFOC."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
from time import perf_counter
from typing import Callable, Mapping, MutableMapping, Sequence

from .datatypes import (
    AdaptivePolicyState,
    MonitoringSignal,
    MonitoringSnapshot,
    OversightRecord,
    OversightSummary,
    PolicyAdjustment,
    PolicyBreach,
    PolicyBreachReport,
    SpendingVelocity,
)


@dataclass
class MonitorState:
    name: str
    last_heartbeat: datetime
    status: str


@dataclass
class PerformanceMetrics:
    """Represents runtime performance insights for a monitored operation."""

    operation_time: float
    cache_hit_rate: float
    memory_usage: float
    parallel_efficiency: float


class AFOCPerformanceMonitor:
    """Tracks timing and cache efficiency across AFOC operations."""

    def __init__(self) -> None:
        self.metrics: MutableMapping[str, PerformanceMetrics] = {}
        self._invocations: MutableMapping[str, int] = {}
        self._cache_hits: MutableMapping[str, int] = {}

    # ------------------------------------------------------------------
    # Cache tracking
    # ------------------------------------------------------------------
    def record_cache_event(self, operation_name: str, hit: bool) -> None:
        total = self._invocations.get(operation_name, 0) + 1
        hits = self._cache_hits.get(operation_name, 0) + (1 if hit else 0)
        self._invocations[operation_name] = total
        self._cache_hits[operation_name] = hits
        self._update_cache_rate(operation_name)

    def _update_cache_rate(self, operation_name: str) -> None:
        total = self._invocations.get(operation_name, 0)
        if total == 0:
            return
        hit_rate = self._cache_hits.get(operation_name, 0) / total
        metrics = self.metrics.get(operation_name)
        if metrics:
            self.metrics[operation_name] = PerformanceMetrics(
                operation_time=metrics.operation_time,
                cache_hit_rate=hit_rate,
                memory_usage=metrics.memory_usage,
                parallel_efficiency=metrics.parallel_efficiency,
            )
        else:
            self.metrics[operation_name] = PerformanceMetrics(
                operation_time=0.0,
                cache_hit_rate=hit_rate,
                memory_usage=0.0,
                parallel_efficiency=0.0,
            )

    # ------------------------------------------------------------------
    # Timing utilities
    # ------------------------------------------------------------------
    def time_call(self, operation_name: str, fn: Callable[..., object], *args, **kwargs):
        start = perf_counter()
        result = fn(*args, **kwargs)
        duration = perf_counter() - start
        metrics = self.metrics.get(operation_name)
        cache_hit_rate = metrics.cache_hit_rate if metrics else 0.0
        self.metrics[operation_name] = PerformanceMetrics(
            operation_time=duration,
            cache_hit_rate=cache_hit_rate,
            memory_usage=metrics.memory_usage if metrics else 0.0,
            parallel_efficiency=metrics.parallel_efficiency if metrics else 0.0,
        )
        return result

    def time_operation(self, operation_name: str):
        def decorator(func: Callable[..., object]):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return self.time_call(operation_name, func, *args, **kwargs)

            return wrapper

        return decorator


class FiscalMonitor:
    """Continuous fiscal monitoring with dual oversight."""

    def __init__(self) -> None:
        self._signals: list[MonitoringSignal] = []
        self._policy_state = AdaptivePolicyState(policies=[])

    def initialize(self, policies: Sequence[PolicyAdjustment]) -> None:
        self._policy_state = AdaptivePolicyState(policies=list(policies))

    def capture_signal(self, signal: MonitoringSignal) -> None:
        self._signals.append(signal)

    def snapshot(self) -> MonitoringSnapshot:
        return MonitoringSnapshot(signals=list(self._signals))

    def compute_spending_velocity(
        self, spending: Mapping[str, float]
    ) -> Sequence[SpendingVelocity]:
        velocities = []
        for phase, amount in spending.items():
            alert = "normal"
            velocity = amount / (len(spending) or 1)
            if velocity > 1.5:
                alert = "high"
            elif velocity < 0.5:
                alert = "low"
            velocities.append(SpendingVelocity(phase=phase, velocity=velocity, alert_level=alert))
        return velocities

    def evaluate_policies(self) -> AdaptivePolicyState:
        now = datetime.utcnow()
        refreshed = []
        for policy in self._policy_state.policies:
            refreshed.append(
                PolicyAdjustment(
                    policy_name=policy.policy_name,
                    adjustment_value=policy.adjustment_value * 0.98,
                    justification=policy.justification,
                    effective_date=now,
                )
            )
        self._policy_state = AdaptivePolicyState(policies=refreshed)
        return self._policy_state

    def detect_policy_breaches(self, snapshot: MonitoringSnapshot) -> PolicyBreachReport:
        breaches = []
        for signal in snapshot.signals:
            if signal.status == "critical":
                breaches.append(
                    PolicyBreach(
                        policy_name=signal.signal_name,
                        severity="critical",
                        deviation=signal.value,
                        remediation_steps=["Escalate to CFO", "Trigger adaptive budget review"],
                    )
                )
        return PolicyBreachReport(breaches=breaches)

    def summarize_oversight(self, records: Sequence[OversightRecord]) -> OversightSummary:
        if not records:
            return OversightSummary(
                records=[], strategic_average=0.0, fiscal_average=0.0, total_budget_consumed=0.0
            )
        strategic_avg = sum(record.strategic_score for record in records) / len(records)
        fiscal_avg = sum(record.fiscal_score for record in records) / len(records)
        total_budget = sum(record.budget_consumed for record in records)
        return OversightSummary(
            records=records,
            strategic_average=strategic_avg,
            fiscal_average=fiscal_avg,
            total_budget_consumed=total_budget,
        )

    def policy_refresh_needed(self, horizon_days: int = 30) -> bool:
        if not self._policy_state.policies:
            return True
        latest = max(policy.effective_date for policy in self._policy_state.policies)
        return datetime.utcnow() - latest > timedelta(days=horizon_days)
