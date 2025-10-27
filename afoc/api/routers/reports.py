"""Reporting API routes."""

from fastapi import APIRouter

from ...services import aggregator

router = APIRouter()


@router.post("/")
def generate(payload: dict) -> dict:
    """Return a combined report."""

    anomalies = payload.get("anomalies", [])
    forecast = payload.get("forecast", [])
    return aggregator.build_report(anomalies, forecast)
