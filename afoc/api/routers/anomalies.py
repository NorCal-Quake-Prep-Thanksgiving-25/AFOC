"""Anomaly API routes."""

from fastapi import APIRouter

from ...services import anomalies as anomaly_service

router = APIRouter()


@router.post("/")
def detect(payload: list[dict]) -> dict:
    """Detect anomalies from the provided payload."""

    return {"results": anomaly_service.detect_anomalies(payload)}
