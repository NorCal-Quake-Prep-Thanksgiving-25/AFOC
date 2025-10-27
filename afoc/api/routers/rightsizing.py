"""Right-sizing API routes."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..security import enforce_security

router = APIRouter(dependencies=[Depends(enforce_security)])


class RightsizingOptionModel(BaseModel):
    """Describe an alternative instance configuration."""

    instance_type: str
    price: float
    cpu_capacity: float
    memory_capacity: float


class RightsizingInventoryModel(BaseModel):
    """Inventory payload supplied by callers."""

    resource_id: str
    instance_type: str
    price: float
    region: str | None = None
    cpu_capacity: float = Field(1.0, gt=0)
    memory_capacity: float = Field(1.0, gt=0)
    metadata: dict | None = None
    options: List[RightsizingOptionModel] | None = None


class RightsizingUtilizationModel(BaseModel):
    """Utilization statistics for each resource."""

    resource_id: str
    p95_cpu: float | None = None
    p95_mem: float | None = None


class RightsizingRequest(BaseModel):
    """Request payload for right-sizing analysis."""

    inventory: List[RightsizingInventoryModel]
    utilization: List[RightsizingUtilizationModel]
    headroom: float = Field(0.15, ge=0)
    policy: str = Field("cost", min_length=1)


@router.post("/rightsize")
def recommend(payload: RightsizingRequest) -> List[dict]:
    """Return right-sizing recommendations."""

    try:
        from ...services import rightsizing as service
    except ImportError as exc:  # pragma: no cover - triggered when dependencies missing
        raise HTTPException(
            status_code=503, detail="rightsizing service unavailable"
        ) from exc

    inventory_records = []
    for item in payload.inventory:
        record = item.model_dump()
        metadata = dict(record.get("metadata") or {})
        option_records = record.pop("options", None)
        if option_records:
            metadata["options"] = option_records
        else:
            metadata.setdefault("options", [])
        metadata.setdefault("price", record["price"])
        metadata.setdefault("cpu_capacity", record["cpu_capacity"])
        metadata.setdefault("memory_capacity", record["memory_capacity"])
        record["metadata"] = metadata
        inventory_records.append(record)
    utilization_records = [item.model_dump() for item in payload.utilization]
    return service.generate_recommendations(
        inventory_records,
        utilization_records,
        headroom=payload.headroom,
        policy=payload.policy,
    )
