"""Dynamic resource orchestration logic for the AFOC."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from .datatypes import (
    ResourceOrchestration,
    ResourceRecommendation,
    ResourceRecommendationSet,
    ResourceShift,
    ReallocationReport,
)


@dataclass
class ResourceSnapshot:
    """Internal representation of model resource utilisation."""

    model_name: str
    cpu_hours: float
    gpu_hours: float
    memory_gb: float
    throughput: float
    performance_score: float

    def cost_signature(self) -> float:
        return self.cpu_hours * 0.1 + self.gpu_hours * 0.4 + self.memory_gb * 0.05


class ResourceConductor:
    """Calculates optimal resource allocations across AI models."""

    def __init__(self) -> None:
        self._history: list[ResourceSnapshot] = []

    def orchestrate_resources(self, fiscal_framework: Mapping[str, float]) -> ResourceOrchestration:
        current = self.get_current_resource_map()
        allocation = self.calculate_optimal_allocation(fiscal_framework)
        plan = self.generate_orchestration_plan(allocation)
        return ResourceOrchestration(current, plan.optimal_distribution, plan.migration_plan, plan.predicted_efficiency_gain)

    # Framework integration -------------------------------------------------
    def calculate_optimal_allocation(self, fiscal_framework: Mapping[str, float]) -> Mapping[str, float]:
        total = sum(fiscal_framework.values()) or 1.0
        return {name: budget / total for name, budget in fiscal_framework.items()}

    def generate_orchestration_plan(self, allocation: Mapping[str, float]):
        current = self.get_current_resource_map()
        migration_plan: list[str] = []
        efficiency: dict[str, float] = {}
        for model, target in allocation.items():
            current_share = current.get(model, 0.0)
            delta = target - current_share
            if abs(delta) < 0.01:
                continue
            direction = "increase" if delta > 0 else "decrease"
            migration_plan.append(f"{direction} allocation for {model} by {abs(delta):.2%}")
            efficiency[model] = (target - current_share) * 10
        return type(
            "Plan",
            (),
            {
                "optimal_distribution": allocation,
                "migration_plan": migration_plan,
                "predicted_efficiency_gain": efficiency,
            },
        )

    def get_current_resource_map(self) -> Mapping[str, float]:
        if not self._history:
            return {}
        total_cost = sum(snapshot.cost_signature() for snapshot in self._history)
        if total_cost == 0:
            return {snapshot.model_name: 0.0 for snapshot in self._history}
        return {
            snapshot.model_name: snapshot.cost_signature() / total_cost
            for snapshot in self._history
        }

    # Adaptive orchestration ------------------------------------------------
    def analyse_performance(self, snapshots: Sequence[ResourceSnapshot]) -> ResourceRecommendationSet:
        recommendations: list[ResourceRecommendation] = []
        for snapshot in snapshots:
            efficiency = snapshot.performance_score / (snapshot.cost_signature() or 1.0)
            if efficiency < 0.8:
                recommendations.append(
                    ResourceRecommendation(
                        model_name=snapshot.model_name,
                        action="reduce",
                        delta=0.05,
                        justification="Underperforming against cost signature",
                    )
                )
            elif efficiency > 1.2:
                recommendations.append(
                    ResourceRecommendation(
                        model_name=snapshot.model_name,
                        action="increase",
                        delta=0.07,
                        justification="High efficiency merits additional resources",
                    )
                )
        return ResourceRecommendationSet(recommendations)

    def execute_reallocation_plan(self, plan: ResourceRecommendationSet) -> ReallocationReport:
        moves: list[ResourceShift] = []
        total_gain = 0.0
        risk = {}
        for rec in plan.recommendations:
            amount = rec.delta
            justification = rec.justification
            if rec.action == "reduce":
                moves.append(
                    ResourceShift(
                        source=rec.model_name,
                        destination="fiscal_reserve",
                        amount=amount,
                        justification=justification,
                    )
                )
                total_gain += amount * 5
            else:
                moves.append(
                    ResourceShift(
                        source="fiscal_reserve",
                        destination=rec.model_name,
                        amount=amount,
                        justification=justification,
                    )
                )
                total_gain += amount * 3
            risk[rec.model_name] = max(0.1, 1 - amount)
        return ReallocationReport(resources_moved=moves, efficiency_gain=total_gain, risk_assessment=risk)

    def record_snapshot(self, snapshot: ResourceSnapshot) -> None:
        self._history.append(snapshot)

    def load_history(self, snapshots: Iterable[ResourceSnapshot]) -> None:
        self._history = list(snapshots)

