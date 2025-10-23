"""Workflow utilities connecting strategic and fiscal oversight."""
from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Callable, List, Mapping, Sequence

from .datatypes import OversightRecord, OversightSummary


@dataclass
class PhaseExecutionResult:
    phase: str
    outcome: Mapping[str, float]
    oversight: OversightRecord


class DualOversight(AbstractContextManager["DualOversight"]):
    """Context manager coordinating strategic and fiscal oversight."""

    def __init__(self, strategic_analyst, fiscal_core) -> None:
        self.strategic_analyst = strategic_analyst
        self.fiscal_core = fiscal_core
        self.records: List[OversightRecord] = []
        self.phase_results: List[PhaseExecutionResult] = []

    def __enter__(self) -> "DualOversight":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def approve_phase(
        self,
        phase_name: str,
        budget_allocation: float,
        execution_fn: Callable[[], Mapping[str, float]],
    ) -> Mapping[str, float]:
        result = execution_fn()
        strategic_score = self.strategic_analyst.review_phase(phase_name, result)
        fiscal_score = min(1.0, budget_allocation / (sum(result.values()) or 1.0))
        record = self.fiscal_core.evaluate_phase(phase_name, strategic_score, fiscal_score, budget_allocation)
        self.records.append(record)
        self.phase_results.append(PhaseExecutionResult(phase=phase_name, outcome=result, oversight=record))
        return result

    def get_strategic_report(self) -> Mapping[str, float]:
        return self.strategic_analyst.generate_strategic_report(self.records)

    def get_fiscal_report(self) -> Mapping[str, float]:
        return self.fiscal_core.get_fiscal_report()

    def calculate_business_impact(self) -> Mapping[str, float]:
        total_roi = sum(record.fiscal_score for record in self.records) / (len(self.records) or 1)
        return {"aggregate_roi_score": total_roi}

    def summary(self) -> OversightSummary:
        return self.fiscal_core.fiscal_monitor.summarize_oversight(self.records)

