"""FastAPI façade exposing the agent mesh."""

from __future__ import annotations

from typing import Any, Dict, List

try:  # pragma: no cover - optional dependency
    from fastapi import Depends, FastAPI, HTTPException, Security, status
    from fastapi.responses import JSONResponse
    from fastapi.security import APIKeyHeader
except Exception:  # pragma: no cover - fallback
    FastAPI = None  # type: ignore
    JSONResponse = None  # type: ignore
    Depends = None  # type: ignore
    HTTPException = None  # type: ignore
    Security = None  # type: ignore
    status = None  # type: ignore
    APIKeyHeader = None  # type: ignore

from .agents import BudgetAgent, ForecastAgent, ROIEngine
from .agents.budget import AllocationRequest
from .agents.forecast import ForecastRequest
from .agents.roi import OptimizationRequest
from .core import ComposableIntelligenceCore
from .auth import APIAuthConfig


def build_api(core: ComposableIntelligenceCore | None = None) -> Any:
    if FastAPI is None:
        raise RuntimeError("FastAPI is required for the API façade")

    if APIKeyHeader is None or Security is None or Depends is None or HTTPException is None:
        raise RuntimeError("FastAPI security dependencies are unavailable")

    if core is None:
        resolved_core = ComposableIntelligenceCore()
    else:
        resolved_core = core

    app = FastAPI(title="Composable Intelligence Core")

    auth_config = APIAuthConfig.from_env()
    api_key_scheme = APIKeyHeader(name=auth_config.header_name, auto_error=False)

    def _authorise(api_key: str | None = Security(api_key_scheme)) -> None:
        if not auth_config.verify(api_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key",
            )

    @app.post("/allocate")
    async def allocate(request: AllocationRequest, _: None = Depends(_authorise)) -> Dict[str, Any]:
        result = await resolved_core.budget_agent.allocate(request)
        return result.dict()

    @app.post("/forecast")
    async def forecast(request: ForecastRequest, _: None = Depends(_authorise)) -> Dict[str, Any]:
        result = await resolved_core.forecast_agent.forecast(request)
        return result.dict()

    @app.post("/optimize")
    async def optimize(
        request: OptimizationRequest, _: None = Depends(_authorise)
    ) -> Dict[str, Any]:
        result = await resolved_core.roi_engine.optimize(request)
        return result.dict()

    @app.post("/optimize/quantum")
    async def optimize_quantum(request: OptimizationRequest, _: None = Depends(_authorise)) -> Any:
        result = await resolved_core.roi_engine.optimize(request)
        if not result.quantum_summary:
            if JSONResponse is None:
                raise RuntimeError("Quantum optimisation unavailable")
            return JSONResponse(
                status_code=503, content={"detail": "Quantum optimiser unavailable"}
            )
        payload: Dict[str, Any] = result.dict()
        return {
            "selected_action": payload["selected_action"],
            "quantum_summary": payload["quantum_summary"],
        }

    @app.post("/audit")
    async def audit(_: None = Depends(_authorise)) -> Dict[str, Any]:
        alert = await resolved_core.security_guardian.audit()
        return alert.dict()

    @app.post("/ingest")
    async def ingest(
        records: List[Dict[str, Any]], _: None = Depends(_authorise)
    ) -> Dict[str, Any]:
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
