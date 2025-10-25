"""Predictive budget intelligence system for the AFOC."""
from __future__ import annotations

from dataclasses import dataclass
import math
import statistics
from typing import Iterable, Mapping, Sequence

from .datatypes import (
    AdaptiveBudget,
    AdaptiveBudgetOutcome,
    BudgetInsight,
    BudgetIntelligenceReport,
    BudgetScenario,
    FiscalForecast,
    ForecastAccuracy,
    ForecastAudit,
    ForecastAuditTrail,
    ForecastDrift,
    ForecastDriftReport,
    StrategicRoadmap,
)


@dataclass
class ForecastModel:
    name: str
    accuracy_history: list[float]
    bias: float

    def update_accuracy(self, new_accuracy: float) -> None:
        self.accuracy_history.append(new_accuracy)
        if len(self.accuracy_history) > 50:
            self.accuracy_history.pop(0)

    def average_accuracy(self) -> float:
        if not self.accuracy_history:
            return 0.0
        return sum(self.accuracy_history) / len(self.accuracy_history)


class BudgetCore:
    """Anchors economic intelligence within the AFOC."""

    def __init__(self) -> None:
        self._forecast_models: dict[str, ForecastModel] = {}

    def predictive_budget_forecasting(self, strategic_roadmap: StrategicRoadmap) -> FiscalForecast:
        requirements = self.forecast_budget_needs(strategic_roadmap)
        savings = self.identify_future_savings(strategic_roadmap)
        risks = self.assess_future_fiscal_risks(strategic_roadmap)
        strategies = self.generate_fiscal_strategies(strategic_roadmap)
        return FiscalForecast(requirements, savings, risks, strategies)

    def forecast_budget_needs(self, roadmap: StrategicRoadmap) -> Mapping[str, float]:
        base = roadmap.growth_projection
        return {milestone: base * (idx + 1) for idx, milestone in enumerate(roadmap.milestones)}

    def identify_future_savings(self, roadmap: StrategicRoadmap) -> Mapping[str, float]:
        return {milestone: roadmap.fiscal_targets.get(milestone, 0) * 0.1 for milestone in roadmap.milestones}

    def assess_future_fiscal_risks(self, roadmap: StrategicRoadmap) -> Mapping[str, float]:
        return {milestone: max(0.1, 1 - roadmap.scenario_assumptions.get(milestone, 0.5)) for milestone in roadmap.milestones}

    def generate_fiscal_strategies(self, roadmap: StrategicRoadmap) -> Sequence[str]:
        strategies = []
        for milestone in roadmap.milestones:
            target = roadmap.fiscal_targets.get(milestone, roadmap.growth_projection)
            strategies.append(f"Align investment in {milestone} with target {target:.2f}")
        return strategies

    # Adaptive budgeting ---------------------------------------------------
    def construct_adaptive_budget(self, baseline: Mapping[str, float], adjustments: Mapping[str, float]) -> AdaptiveBudget:
        total_baseline = sum(baseline.values()) or 1.0
        normalized_adjustments = {k: v / total_baseline for k, v in adjustments.items()}
        confidence = 1 - min(0.5, sum(abs(v) for v in normalized_adjustments.values()))
        return AdaptiveBudget(baseline=baseline, adjustments=adjustments, confidence=confidence)

    def apply_adaptive_budget(self, adaptive_budget: AdaptiveBudget) -> AdaptiveBudgetOutcome:
        applied = {
            phase: amount + adaptive_budget.adjustments.get(phase, 0.0)
            for phase, amount in adaptive_budget.baseline.items()
        }
        rationale = [
            f"Adjusted {phase} by {adaptive_budget.adjustments.get(phase, 0.0):.2f} to maintain equilibrium"
            for phase in adaptive_budget.baseline
        ]
        return AdaptiveBudgetOutcome(applied_budget=applied, rationale=rationale, confidence=adaptive_budget.confidence)

    # Forecast evaluation --------------------------------------------------
    def track_forecast_accuracy(self, forecast_id: str, target: float, actual: float) -> ForecastAccuracy:
        accuracy = 1 - abs(target - actual) / (target or 1.0)
        model = self._forecast_models.setdefault(
            forecast_id,
            ForecastModel(name=forecast_id, accuracy_history=[], bias=0.0),
        )
        model.update_accuracy(accuracy)
        return ForecastAccuracy(target=target, actual=actual, confidence=accuracy)

    def audit_forecasts(self) -> ForecastAuditTrail:
        audits = []
        for model in self._forecast_models.values():
            accuracy = model.average_accuracy()
            variance = statistics.pvariance(model.accuracy_history) if len(model.accuracy_history) > 1 else 0.0
            audits.append(
                ForecastAudit(
                    forecast_id=model.name,
                    accuracy=accuracy,
                    variance=variance,
                    commentary="Stable" if accuracy > 0.9 else "Needs recalibration",
                )
            )
        return ForecastAuditTrail(audits=audits)

    def analyse_forecast_drift(self, expected: Mapping[str, float], actual: Mapping[str, float]) -> ForecastDriftReport:
        drifts = []
        commentary = []
        for metric, target in expected.items():
            actual_value = actual.get(metric, 0.0)
            deviation = actual_value - target
            drifts.append(ForecastDrift(metric=metric, predicted=target, actual=actual_value, deviation=deviation))
            if target == 0:
                commentary.append(f"No target set for {metric}")
            else:
                pct = deviation / target
                commentary.append(f"{metric} deviated by {pct:.1%}")
        return ForecastDriftReport(drifts=drifts, commentary=commentary)

    def compile_budget_intelligence(self, forecast: FiscalForecast) -> BudgetIntelligenceReport:
        forecasts = [
            ForecastAccuracy(target=value, actual=value * 0.95, confidence=0.95)
            for value in forecast.projected_budget_requirements.values()
        ]
        scenarios = [
            BudgetScenario(
                scenario_name="baseline",
                baseline_allocation=forecast.projected_budget_requirements,
                stress_tests={k: v * 1.2 for k, v in forecast.projected_budget_requirements.items()},
                success_probability=0.8,
                commentary="Stable outlook",
            )
        ]
        insights = [
            BudgetInsight(
                title="Cost efficiency",
                description="Projected savings opportunities identified",
                impact=sum(forecast.future_cost_optimization_opportunities.values()),
            )
        ]
        recommendations = [
            "Invest in automation to sustain savings",
            "Tighten monitoring on high risk milestones",
        ]
        return BudgetIntelligenceReport(
            forecasts=forecasts,
            scenarios=scenarios,
            insights=insights,
            recommendations=recommendations,
        )

