"""Quantum-level ROI analytics for the EliteAI commercial suite."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .datatypes import CompetitiveGapAnalysis, QuantumROIReport


@dataclass
class _IndustryBaseline:
    cost_savings_multiplier: float
    revenue_growth_multiplier: float
    risk_mitigation_multiplier: float


_BASELINES: Mapping[str, _IndustryBaseline] = {
    "finance": _IndustryBaseline(0.22, 0.28, 0.18),
    "healthcare": _IndustryBaseline(0.25, 0.24, 0.2),
    "consulting": _IndustryBaseline(0.2, 0.3, 0.16),
    "government": _IndustryBaseline(0.18, 0.22, 0.25),
    "energy": _IndustryBaseline(0.26, 0.27, 0.21),
}


class QuantumROIEngine:
    """Calculates multi-dimensional ROI scores for enterprise clients."""

    def __init__(self, strategic_premium: float = 0.12) -> None:
        self.strategic_premium = strategic_premium

    def calculate_multi_dimensional_roi(
        self,
        client_industry: str,
        company_size: str,
        strategic_goals: Sequence[str],
    ) -> QuantumROIReport:
        baseline = _BASELINES.get(client_industry.lower(), _IndustryBaseline(0.2, 0.2, 0.2))
        scale_factor = self._company_size_modifier(company_size)
        ambition_multiplier = 1 + (0.02 * len(strategic_goals))

        financial_metrics = {
            "cost_savings": round(50_0000 * baseline.cost_savings_multiplier * scale_factor, 2),
            "revenue_acceleration": round(
                65_0000 * baseline.revenue_growth_multiplier * scale_factor, 2
            ),
            "risk_mitigation_value": round(
                45_0000 * baseline.risk_mitigation_multiplier * scale_factor, 2
            ),
            "strategic_option_value": round(
                25_0000 * self.strategic_premium * ambition_multiplier, 2
            ),
        }

        competitive_metrics = {
            "time_to_market_acceleration": "6-12 months faster than competitors",
            "innovation_velocity": f"{2 + len(strategic_goals) * 0.3:.1f}x more innovation output",
            "talent_attraction_premium": "25-40% easier to hire top talent",
            "market_leadership_duration": "2-3 years competitive advantage",
        }

        future_metrics = {
            "ai_adoption_curve": "18-24 months ahead of industry peers",
            "digital_resilience_score": "85%+ higher than industry average",
            "strategic_agility_index": "Can pivot 3x faster than competitors",
        }

        return QuantumROIReport(
            financial_metrics=financial_metrics,
            competitive_metrics=competitive_metrics,
            future_metrics=future_metrics,
        )

    def generate_competitive_analysis(
        self, client_vs_competitors: Mapping[str, float]
    ) -> CompetitiveGapAnalysis:
        delta = sum(client_vs_competitors.values()) / max(len(client_vs_competitors), 1)
        advantage = "$50M-$200M market cap impact"
        if delta > 0.3:
            advantage = "$200M-$400M market cap impact"

        operational_superiority = "40-70% lower operating costs"
        if client_vs_competitors.get("efficiency", 0.0) > 0.4:
            operational_superiority = "55-80% lower operating costs"

        strategic_positioning = "3-5 market positions gained in 24 months"
        if client_vs_competitors.get("innovation", 0.0) > 0.5:
            strategic_positioning = "4-6 market positions gained in 18 months"

        return CompetitiveGapAnalysis(
            first_mover_advantage=advantage,
            operational_superiority=operational_superiority,
            strategic_positioning=strategic_positioning,
        )

    @staticmethod
    def _company_size_modifier(company_size: str) -> float:
        size = company_size.lower()
        if size in {"startup", "scaleup"}:
            return 0.6
        if size in {"mid_market", "midmarket"}:
            return 0.9
        if size in {"enterprise", "global"}:
            return 1.3
        return 1.0
