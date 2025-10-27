"""Ingestion API routes."""

from fastapi import APIRouter

from ...ingest import load_placeholder_dataset

router = APIRouter()


@router.get("/sample")
def read_sample() -> list[dict]:
    """Return a sample of ingested data."""

    return load_placeholder_dataset()
