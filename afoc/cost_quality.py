"""Cost-quality equilibrium management for the AFOC."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

import statistics

from .datatypes import (
    CostDrift,
    CostDriftAnalysis,
    CostQualityDirective,
    CostQualityPlan,
    CostQualitySnapshot,
    CostQualitySnapshotEnvelope,
    EquilibriumPoint,
    FiscalEquilibriumState,
    QualitySignal,
    QualitySignalBatch,
)


@dataclass
class CostQualityMetric:
    component: str
    cost: float
    quality: float
    benchmark_cost: float
    benchmark_quality: float

    def cost_delta(self) -> float:
        return self.cost - self.benchmark_cost

    def quality_delta(self) -> float:
        return self.quality - self.benchmark_quality

    def efficiency(self) -> float:
        denominator = self.cost or 1.0
        return self.quality / denominator


class CostQualityEngine:
    """Maintains cost-quality equilibrium across multiple components."""

    def __init__(self) -> None:
        self._history: list[CostQualityMetric] = []

    def maintain_equilibrium(
        self, operational_data: Sequence[CostQualityMetric]
    ) -> FiscalEquilibriumState:
        frontier = self.calculate_equilibrium_frontier(operational_data)
        directives = self.generate_optimization_directives(frontier)
        state = FiscalEquilibriumState(
            current_equilibrium=self.measure_current_balance(operational_data),
            optimal_targets=directives.optimal_points,
            adjustment_actions=directives.required_actions,
            efficiency_gains=directives.expected_improvements,
        )
        self._history.extend(operational_data)
        return state

    def calculate_equilibrium_frontier(
        self, metrics: Sequence[CostQualityMetric]
    ) -> CostQualitySnapshotEnvelope:
        snapshot = self._build_snapshot(metrics)
        plan = self._build_plan(snapshot)
        return CostQualitySnapshotEnvelope(snapshot, plan)

    def generate_optimization_directives(
        self, envelope: CostQualitySnapshotEnvelope
    ) -> CostQualityPlan:
        return envelope.directives

    def measure_current_balance(self, metrics: Sequence[CostQualityMetric]) -> Mapping[str, float]:
        return {metric.component: metric.efficiency() for metric in metrics}

    def _build_snapshot(self, metrics: Sequence[CostQualityMetric]) -> CostQualitySnapshot:
        components = {metric.component: (metric.cost, metric.quality) for metric in metrics}
        equilibrium = {metric.component: metric.efficiency() for metric in metrics}
        anomalies = [
            metric.component
            for metric in metrics
            if abs(metric.cost_delta()) > metric.benchmark_cost * 0.15
        ]
        return CostQualitySnapshot(components, equilibrium, anomalies)

    def _build_plan(self, snapshot: CostQualitySnapshot) -> CostQualityPlan:
        directives: list[CostQualityDirective] = []
        optimal_points: dict[str, float] = {}
        required_actions: list[str] = []
        expected_improvements: dict[str, float] = {}
        for component, (cost, quality) in snapshot.components.items():
            equilibrium = snapshot.equilibrium[component]
            target = (
                statistics.fmean(snapshot.equilibrium.values())
                if snapshot.equilibrium
                else equilibrium
            )
            action = "hold"
            gain = 0.0
            if equilibrium > target * 1.05:
                action = "reinvest"
                gain = (equilibrium - target) * cost
            elif equilibrium < target * 0.95:
                action = "optimize"
                gain = (target - equilibrium) * cost
            directives.append(
                CostQualityDirective(
                    component=component,
                    action=action,
                    expected_gain=gain,
                    confidence=0.8,
                )
            )
            optimal_points[component] = target
            required_actions.append(f"{component}:{action}")
            expected_improvements[component] = gain
        return CostQualityPlan(
            directives=directives,
            optimal_points=optimal_points,
            required_actions=required_actions,
            expected_improvements=expected_improvements,
        )

    def analyse_cost_drifts(self, metrics: Sequence[CostQualityMetric]) -> CostDriftAnalysis:
        drifts = []
        for metric in metrics:
            deviation = metric.cost_delta()
            if abs(deviation) > metric.benchmark_cost * 0.1:
                drifts.append(
                    CostDrift(
                        component=metric.component,
                        observed_cost=metric.cost,
                        expected_cost=metric.benchmark_cost,
                        deviation=deviation,
                    )
                )
        recommendations = []
        if drifts:
            for drift in drifts:
                if drift.deviation > 0:
                    recommendations.append(
                        f"Reduce spending on {drift.component} by {abs(drift.deviation):.2f}"
                    )
                else:
                    recommendations.append(
                        f"Consider reinvestment into {drift.component} to capture additional value"
                    )
        return CostDriftAnalysis(drifts=drifts, recommendations=recommendations)

    def evaluate_quality_signals(self, signals: QualitySignalBatch) -> Mapping[str, str]:
        assessments = {}
        for signal in signals.signals:
            if signal.value >= signal.target:
                assessments[signal.component] = "healthy"
            elif signal.value >= signal.target * 0.9:
                assessments[signal.component] = "monitor"
            else:
                assessments[signal.component] = "degraded"
        return assessments

    def build_quality_improvement_plan(
        self, batch: QualitySignalBatch
    ) -> Mapping[str, Sequence[str]]:
        plan: dict[str, list[str]] = {}
        for signal in batch.signals:
            actions: list[str] = []
            if signal.value < signal.target:
                delta = signal.target - signal.value
                actions.append(f"Allocate quality uplift budget of {delta:.2f} units")
            if signal.value < signal.target * 0.8:
                actions.append("Escalate to quality council for immediate review")
            plan[signal.component] = actions or ["Maintain current quality practices"]
        return plan
