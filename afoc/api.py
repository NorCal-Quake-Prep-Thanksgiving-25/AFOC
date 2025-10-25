"""FastAPI façade exposing the agent mesh."""
from __future__ import annotations

from typing import Any, Dict

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

    app = FastAPI(title="Composable Intelligence Core")
    core = core or ComposableIntelligenceCore()

    @app.post("/allocate")
    async def allocate(request: AllocationRequest) -> Dict[str, Any]:
        result = await core.budget_agent.allocate(request)
        return result.dict()

    @app.post("/forecast")
    async def forecast(request: ForecastRequest) -> Dict[str, Any]:
        result = await core.forecast_agent.forecast(request)
        return result.dict()

    @app.post("/optimize")
    async def optimize(request: OptimizationRequest) -> Dict[str, Any]:
        result = await core.roi_engine.optimize(request)
        return result.dict()

    @app.post("/audit")
    async def audit() -> Dict[str, Any]:
        alert = await core.security_guardian.audit()
        return alert.dict()

    return app
