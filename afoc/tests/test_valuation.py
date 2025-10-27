"""Tests for the valuation service."""

from typing import Mapping

from afoc.services import valuation


def test_compute_value_report_ranges() -> None:
    """Valuation output should respect the documented ranges."""

    inputs = valuation.ValueInputs(
        annual_spend=1_200_000.0,
        anomaly_spend=120_000.0,
        rightsizing_monthly_savings=12_000.0,
        reservable_spend=300_000.0,
        tier="large",
        anomaly_count=6,
    )
    report = valuation.compute_value_report(inputs)

    assert 6_000.0 <= report.anomaly <= 18_000.0
    assert report.rightsize == 144_000.0
    assert 45_000.0 <= report.forecast <= 75_000.0
    assert report.integrated >= report.anomaly + report.rightsize + report.forecast
    assumptions = report.assumptions
    assert isinstance(assumptions, Mapping)
    assert assumptions["tier_multiplier"] == valuation.SYNERGY_MULTIPLIERS["large"]
