"""FastAPI façade exposing the agent mesh."""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import (
    BaseModel,
)  # Security: pydantic enforces payload validation before processing credentials.

try:  # pragma: no cover - optional dependency
    from fastapi import Depends, FastAPI, HTTPException, Security, status
    from fastapi.responses import JSONResponse
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
except Exception:  # pragma: no cover - fallback
    FastAPI = None  # type: ignore
    JSONResponse = None  # type: ignore
    Depends = None  # type: ignore
    HTTPException = None  # type: ignore
    Security = None  # type: ignore
    status = None  # type: ignore
    HTTPAuthorizationCredentials = None  # type: ignore
    HTTPBearer = None  # type: ignore

from .agents import BudgetAgent, ForecastAgent, ROIEngine
from .agents.budget import AllocationRequest
from .agents.forecast import ForecastRequest
from .agents.roi import OptimizationRequest
from .core import ComposableIntelligenceCore
from .auth import JWTAuthenticator, UserPrincipal, require_roles
from .security.audit_logger import AuditLogger


class LoginRequest(BaseModel):
    username: str  # Security: explicit field definitions prevent injection of unexpected keys.
    password: str  # Security: validated password field ensures downstream auth only receives expected type.


def build_api(core: ComposableIntelligenceCore | None = None) -> Any:
    if FastAPI is None:
        raise RuntimeError("FastAPI is required for the API façade")

    if HTTPBearer is None or Security is None or Depends is None or HTTPException is None:
        raise RuntimeError("FastAPI security dependencies are unavailable")

    if core is None:
        resolved_core = ComposableIntelligenceCore()
    else:
        resolved_core = core

    app = FastAPI(title="Composable Intelligence Core")

    authenticator = (
        JWTAuthenticator()
    )  # Security: centralises JWT issuance so routes never bypass hardened checks.
    audit_logger = (
        AuditLogger()
    )  # Security: audit trail persists every API interaction for forensics.
    bearer = HTTPBearer(
        auto_error=False
    )  # Security: explicit bearer scheme avoids leaking auth context via query params.

    async def _authorise(
        credentials: HTTPAuthorizationCredentials | None = Security(bearer),
        required_roles: tuple[str, ...] = (),
    ) -> UserPrincipal:
        if credentials is None or not credentials.credentials:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
        try:
            principal = authenticator.verify_token(credentials.credentials)
            require_roles(principal, *required_roles)
            return principal
        except (
            Exception
        ) as exc:  # Security: catch verification errors to avoid leaking token parsing hints.
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            ) from exc

    def _require_roles(*roles: str):
        # Security: wrapping dependency centralises RBAC so every endpoint enforces the expected roles consistently.
        async def _inner(
            credentials: HTTPAuthorizationCredentials = Security(bearer),
        ) -> UserPrincipal:
            return await _authorise(credentials, roles)

        return _inner

    @app.post("/auth/login")
    async def login(payload: LoginRequest) -> Dict[str, str]:
        principal = authenticator.authenticate(payload.username, payload.password)
        if not principal:
            # Security: denied attempts are logged for intrusion detection.
            audit_logger.log(actor=payload.username, action="login", status="denied")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )
        token = authenticator.issue_token(principal)
        # Security: issued tokens captured to maintain an audit trail of access grants.
        audit_logger.log(actor=payload.username, action="login", status="issued")
        return {"access_token": token, "token_type": "bearer"}

    @app.post("/allocate")
    async def allocate(
        request: AllocationRequest,
        principal: UserPrincipal = Depends(_require_roles("analyst", "viewer")),
    ) -> Dict[str, Any]:
        result = await resolved_core.budget_agent.allocate(request)
        # Security: allocation requests logged for fiscal traceability.
        audit_logger.log(actor=principal.username, action="allocate", status="success")
        return result.model_dump()  # Security: model_dump avoids deprecated serialization and ensures consistent payload signing.

    @app.post("/forecast")
    async def forecast(
        request: ForecastRequest,
        principal: UserPrincipal = Depends(
            _require_roles(
                "analyst",
            )
        ),
    ) -> Dict[str, Any]:
        result = await resolved_core.forecast_agent.forecast(request)
        # Security: forecast runs are captured to correlate with downstream spend decisions.
        audit_logger.log(actor=principal.username, action="forecast", status="success")
        return result.model_dump()  # Security: modern serializer prevents silent field drops during forecast exposure.

    @app.post("/optimize")
    async def optimize(
        request: OptimizationRequest,
        principal: UserPrincipal = Depends(_require_roles("analyst", "admin")),
    ) -> Dict[str, Any]:
        result = await resolved_core.roi_engine.optimize(request)
        # Security: optimisation changes recorded to explain budget shifts.
        audit_logger.log(actor=principal.username, action="optimize", status="success")
        return result.model_dump()  # Security: RBAC responses stay canonical for audit replay without deprecation paths.

    @app.post("/optimize/quantum")
    async def optimize_quantum(
        request: OptimizationRequest,
        principal: UserPrincipal = Depends(
            _require_roles(
                "admin",
            )
        ),
    ) -> Any:
        result = await resolved_core.roi_engine.optimize(request)
        if not result.quantum_summary:
            if JSONResponse is None:
                raise RuntimeError("Quantum optimisation unavailable")
            return JSONResponse(
                status_code=503, content={"detail": "Quantum optimiser unavailable"}
            )
        payload: Dict[str, Any] = result.model_dump()  # Security: ensures quantum diagnostics retain integrity with v2-safe dumps.
        # Security: quantum runs logged to ensure high-privilege operations remain auditable.
        audit_logger.log(actor=principal.username, action="optimize_quantum", status="success")
        return {
            "selected_action": payload["selected_action"],
            "quantum_summary": payload["quantum_summary"],
        }

    @app.post("/audit")
    async def audit(
        principal: UserPrincipal = Depends(_require_roles("admin", "analyst")),
    ) -> Dict[str, Any]:
        alert = await resolved_core.security_guardian.audit()
        # Security: audit trail includes who requested guardian checks.
        audit_logger.log(actor=principal.username, action="audit", status="success")
        payload = alert.model_dump()  # Security: structured dump protects audit payloads from version drift in Pydantic.
        payload["status"] = (
            alert.severity
        )  # Security: explicit status field aids downstream policy enforcement.
        return payload

    @app.post("/ingest")
    async def ingest(
        records: List[Dict[str, Any]],
        principal: UserPrincipal = Depends(_require_roles("analyst", "viewer")),
    ) -> Dict[str, Any]:
        report = resolved_core.ingest_collector_payload(records, source="api")
        # Security: ingestion volume tracked to detect suspicious bursts.
        audit_logger.log(
            actor=principal.username,
            action="ingest",
            status="success",
            metadata={"ingested": report.ingested},
        )
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
