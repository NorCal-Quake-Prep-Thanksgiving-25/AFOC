"""Ingestion API routes."""

from __future__ import annotations

from datetime import datetime, timedelta
from io import BytesIO
import os
from tempfile import NamedTemporaryFile

import polars as pl
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from ...ingest.loaders import (
    load_aws_cur_csv,
    load_generic_usage_csv,
    load_openai_usage_csv,
)
from ..security import enforce_security

router = APIRouter(dependencies=[Depends(enforce_security)])


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


@router.post("/upload")
async def upload_usage(
    *, kind: str, file: UploadFile = File(...), account: str | None = None
) -> dict:
    """Persist uploaded CSV usage data into the warehouse."""

    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file"
        )

    # Performance: write to a temporary file so the shared Polars loaders can be reused.
    with NamedTemporaryFile(delete=False, suffix=".csv") as handle:
        handle.write(contents)
        tmp_path = handle.name

    try:
        if kind == "openai":
            frame = load_openai_usage_csv(tmp_path)
        elif kind == "aws":
            frame = load_aws_cur_csv(tmp_path)
        elif kind == "generic":
            # Security: require an explicit mapping before loading arbitrary columns.
            dataset = pl.read_csv(BytesIO(contents), try_parse_dates=True)
            mapping = {
                "timestamp": dataset.columns[0],
                "service": dataset.columns[1],
                "cost": dataset.columns[-1],
                "provider": "custom",
                "account": account or "default",
            }
            frame = load_generic_usage_csv(tmp_path, mapping)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported ingestion kind",
            )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
    finally:
        os.unlink(tmp_path)

    return {"rows_ingested": frame.height}
