"""Forecasting API routes."""

from fastapi import APIRouter

from ...services import forecasting as forecasting_service

router = APIRouter()


@router.post("/")
def forecast(payload: list[float]) -> dict:
    """Return a simple forecast for the provided series."""

    return {"results": forecasting_service.generate_forecast(payload)}
