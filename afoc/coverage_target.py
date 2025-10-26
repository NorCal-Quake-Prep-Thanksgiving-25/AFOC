"""Compliance-critical metric helpers kept under coverage enforcement."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Iterable, List


@dataclass
class CoverageMetric:
    """Represents a measurable KPI for the secure orchestration core."""

    name: str
    value: float
    threshold: float

    def status(self) -> str:
        return "pass" if self.is_healthy() else "fail"

    def is_healthy(self) -> bool:
        return self.value >= self.threshold  # Security: deterministic check keeps compliance gating simple to audit.


def summarise_metrics(metrics: Iterable[CoverageMetric]) -> dict[str, float | List[str]]:
    """Aggregate metrics to a small, auditable payload for CI checks."""

    metrics = list(metrics)
    if not metrics:
        raise ValueError("metrics must not be empty")  # Security: failing fast prevents silent compliance drift.
    pass_names = [metric.name for metric in metrics if metric.is_healthy()]
    fail_names = [metric.name for metric in metrics if not metric.is_healthy()]
    average = mean(metric.value for metric in metrics)
    return {
        "average": average,  # Security: average ensures CI gate can reason about fleet-wide posture quickly.
        "passes": pass_names,
        "failures": fail_names,
    }
