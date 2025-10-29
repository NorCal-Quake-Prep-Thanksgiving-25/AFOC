"""Implementation of the :class:`FiscalCognitionUnit`.

The cognition unit acts as a chief-fiscal-officer-in-a-box.  Its primary
responsibility is to translate high-level strategic intents into a fiscal map
that the remainder of the AFOC can use.  The algorithms implemented here favour
interpretability.  They rely on heuristics and moving averages which makes them
appropriate for deterministic unit testing while still being rich enough to
simulate a complex fiscal environment.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from .datatypes import FiscalCognitiveMap, StrategicRoadmap, StrategicRequest


@dataclass
class TrendSignal:
    """Simple signal representation used internally by the cognition unit."""

    name: str
    current_value: float
    historical_average: float
    volatility: float

    def stability_index(self) -> float:
        if self.historical_average == 0:
            return 0.0
        deviation = abs(self.current_value - self.historical_average)
        return 1.0 - min(1.0, deviation / (self.historical_average + self.volatility + 1e-6))


class FiscalCognitionUnit:
    """Transforms strategic intentions into actionable fiscal intelligence."""

    def __init__(self) -> None:
        self._trend_library: Mapping[str, TrendSignal] = {}

    def ingest_signals(self, signals: Iterable[TrendSignal]) -> None:
        """Loads trend signals into the cognition library."""

        self._trend_library = {signal.name: signal for signal in signals}

    # Public API -----------------------------------------------------------
    def analyze_fiscal_landscape(self, strategic_goals: StrategicRequest) -> FiscalCognitiveMap:
        """Return a high fidelity fiscal map for the provided goals."""

        flow_dynamics = self.model_resource_flows(strategic_goals)
        tradeoffs = self.quantify_tradeoff_curves(strategic_goals)
        investments = self.optimize_investment_allocation(strategic_goals)
        returns = self.calculate_risk_adjusted_roi(strategic_goals)
        return FiscalCognitiveMap(flow_dynamics, tradeoffs, investments, returns)

    # Sub routines ---------------------------------------------------------
    def model_resource_flows(self, strategic_goals: StrategicRequest) -> Mapping[str, float]:
        """Estimate ideal resource flows based on objectives and constraints."""

        baseline = strategic_goals.expected_roi
        flows = {
            objective: min(baseline * weight, 100.0)
            for objective, weight in strategic_goals.constraints.items()
        }
        normalization = sum(flows.values()) or 1.0
        return {name: value / normalization for name, value in flows.items()}

    def quantify_tradeoff_curves(self, strategic_goals: StrategicRequest) -> Mapping[str, tuple[float, float]]:
        """Derive cost-quality trade-offs for each strategic constraint."""

        tradeoffs = {}
        for constraint, weight in strategic_goals.constraints.items():
            tradeoffs[constraint] = (weight * strategic_goals.expected_roi, 1.0 - weight)
        return tradeoffs

    def optimize_investment_allocation(self, strategic_goals: StrategicRequest) -> Mapping[str, float]:
        """Compute optimal investment distribution for each goal."""

        total_weight = sum(strategic_goals.constraints.values()) or 1.0
        return {
            name: (weight / total_weight) * strategic_goals.expected_roi
            for name, weight in strategic_goals.constraints.items()
        }

    def calculate_risk_adjusted_roi(self, strategic_goals: StrategicRequest) -> Mapping[str, float]:
        """Estimate risk-adjusted returns using internal trend stability."""

        risk_adjusted = {}
        for name, weight in strategic_goals.constraints.items():
            trend = self._trend_library.get(name)
            stability = trend.stability_index() if trend else 0.5
            risk_adjusted[name] = strategic_goals.expected_roi * weight * stability
        return risk_adjusted

    # Forecasting ---------------------------------------------------------
    def generate_roadmap_alignment(self, roadmap: StrategicRoadmap) -> Mapping[str, float]:
        """Score roadmap milestones using the cognition model."""

        scores = {}
        for milestone in roadmap.milestones:
            base = roadmap.fiscal_targets.get(milestone, roadmap.growth_projection)
            trend = self._trend_library.get(milestone)
            modifier = trend.stability_index() if trend else 0.7
            scores[milestone] = base * modifier
        return scores

    def recommend_focus_areas(self, roadmap: StrategicRoadmap, top_n: int = 3) -> Sequence[str]:
        """Return the highest priority focus areas for leadership."""

        alignment = self.generate_roadmap_alignment(roadmap)
        ranked = sorted(alignment.items(), key=lambda item: item[1], reverse=True)
        return [name for name, _ in ranked[:top_n]]

