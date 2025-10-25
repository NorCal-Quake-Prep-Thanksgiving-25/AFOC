"""Security guardian agent enforcing zero-trust posture."""
from __future__ import annotations

import time
from typing import Dict, List

from ..pydantic_compat import BaseModel, Field

from .event_bus import AgentEvent, AsyncEventBus


class SecurityAlert(BaseModel):
    severity: str
    message: str
    timestamp: float = Field(default_factory=time.time)


class _AuditContext(BaseModel):
    repositories: List[str] = Field(default_factory=list)
    signed_commits: bool = True
    sbom_generated: bool = False


class SecurityGuardian:
    """Validates security controls before allowing actions."""

    def __init__(self, event_bus: AsyncEventBus | None = None) -> None:
        self._event_bus = event_bus
        self._last_audit: Dict[str, bool] = {}
        if event_bus:
            event_bus.subscribe("security.alert", self._noop)

    def bind_event_bus(self, event_bus: AsyncEventBus) -> None:
        self._event_bus = event_bus
        event_bus.subscribe("security.alert", self._noop)

    async def audit(self, context: _AuditContext | None = None) -> SecurityAlert:
        ctx = context or _AuditContext()
        missing_controls = []
        if not ctx.signed_commits:
            missing_controls.append("Signed commits disabled")
        if not ctx.sbom_generated:
            missing_controls.append("SBOM missing")
        if missing_controls:
            message = "; ".join(missing_controls)
            alert = SecurityAlert(severity="high", message=message)
        else:
            alert = SecurityAlert(severity="info", message="Security posture verified")
        if self._event_bus:
            await self._event_bus.publish(
                AgentEvent(type="security.alert", payload=alert.dict())
            )
        return alert

    async def _noop(self, event: AgentEvent) -> None:  # pragma: no cover - async hook
        return None

    @property
    def last_audit_status(self) -> Dict[str, bool]:
        return dict(self._last_audit)
