"""Right-sizing API routes."""

from fastapi import APIRouter

from ...services import rightsizing as rightsizing_service

router = APIRouter()


@router.post("/")
def recommend(payload: list[dict]) -> dict:
    """Return right-sizing recommendations."""

    return {"results": rightsizing_service.generate_recommendations(payload)}
