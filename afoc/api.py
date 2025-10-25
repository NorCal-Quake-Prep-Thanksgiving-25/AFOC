"""FastAPI façade exposing the agent mesh."""

from __future__ import annotations

from typing import Any, Dict, List

try:  # pragma: no cover - optional dependency
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
except Exception:  # pragma: no cover - fallback
    FastAPI = None  # type: ignore
    JSONResponse = None  # type: ignore

from .agents import BudgetAgent, ForecastAgent, ROIEngine
from .agents.budget import AllocationRequest
from .agents.forecast import ForecastRequest
from .agents.roi import OptimizationRequest
from .core import ComposableIntelligenceCore


def build_api(core: ComposableIntelligenceCore | None = None) -> Any:
    if FastAPI is None:
        raise RuntimeError("FastAPI is required for the API façade")

    if core is None:
        resolved_core = ComposableIntelligenceCore()
    else:
        resolved_core = core

    app = FastAPI(title="Composable Intelligence Core")

    @app.post("/allocate")
    async def allocate(request: AllocationRequest) -> Dict[str, Any]:
        result = await resolved_core.budget_agent.allocate(request)
        return result.dict()

    @app.post("/forecast")
    async def forecast(request: ForecastRequest) -> Dict[str, Any]:
        result = await resolved_core.forecast_agent.forecast(request)
        return result.dict()

    @app.post("/optimize")
    async def optimize(request: OptimizationRequest) -> Dict[str, Any]:
        result = await resolved_core.roi_engine.optimize(request)
        return result.dict()

    @app.post("/audit")
    async def audit() -> Dict[str, Any]:
        alert = await resolved_core.security_guardian.audit()
        return alert.dict()

    @app.post("/ingest")
    async def ingest(records: List[Dict[str, Any]]) -> Dict[str, Any]:
        report = resolved_core.ingest_collector_payload(records, source="api")
        return {
            "ingested": report.ingested,
            "cached": report.cached,
            "failed": report.failed,
            "completed_at": report.completed_at.isoformat(),
        }

    @app.get("/health")
    async def health() -> Dict[str, Any]:
        return resolved_core.healthcheck()

    return app
