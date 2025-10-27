"""Aggregation services for reporting."""

from typing import Dict, List


def build_report(anomalies: List[dict], forecasts: List[float]) -> Dict[str, object]:
    """Combine anomalies and forecast information into a basic report."""

    return {"anomalies": anomalies, "forecast": forecasts}
