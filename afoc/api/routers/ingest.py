"""Ingestion API routes."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter

router = APIRouter()


def _generate_sample(days: int = 7) -> list[dict]:
    base = datetime.utcnow() - timedelta(days=days)
    return [
        {
            "ts": (base + timedelta(days=offset)).isoformat(),
            "provider": "demo",
            "service": "compute",
            "account": "sandbox",
            "cost_usd": 100 + 5 * offset,
        }
        for offset in range(days)
    ]


@router.get("/sample")
def read_sample() -> list[dict]:
    """Return a generated sample of ingested data."""

    return _generate_sample()
