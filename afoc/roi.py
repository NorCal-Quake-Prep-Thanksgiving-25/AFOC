"""ROI intelligence for the AFOC."""
from __future__ import annotations

from typing import Mapping, Sequence

from .datatypes import ROIInsight, ROIIntelligence, ROIReport, ROIThresholdBreach


class ValueReturnCalculator:
    """Calculates ROI metrics and detects threshold breaches."""

    def compute_roi(self, cost: float, benefit: float) -> float:
        if cost == 0:
            return 0.0
        return (benefit - cost) / cost

    def generate_report(self, data: Mapping[str, tuple[float, float]], thresholds: Mapping[str, float]) -> ROIIntelligence:
        insights = []
        breaches = []
        total_roi = 0.0
        for initiative, (cost, benefit) in data.items():
            roi = self.compute_roi(cost, benefit)
            insights.append(
                ROIInsight(
                    initiative=initiative,
                    cost=cost,
                    benefit=benefit,
                    roi=roi,
                    commentary="Healthy" if roi >= 0 else "Needs review",
                )
            )
            total_roi += roi
            threshold = thresholds.get(initiative, 0.0)
            if roi < threshold:
                breaches.append(
                    ROIThresholdBreach(
                        initiative=initiative,
                        threshold=threshold,
                        actual=roi,
                        deviation=threshold - roi,
                    )
                )
        report = ROIReport(insights=insights, aggregate_roi=total_roi / (len(data) or 1), recommendations=["Increase focus on high ROI initiatives"])
        return ROIIntelligence(report=report, breaches=breaches)

