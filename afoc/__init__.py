"""Autonomous Fiscal Orchestration Core package."""
from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

from .core import AutonomousFiscalOrchestrationCore
from .elite_enterprise import EliteAIEnterprisePro, deploy_elite_enterprise_system
from .models import GodTierAIEnterpriseSystem

if TYPE_CHECKING:  # pragma: no cover - import for static analysis only
    from .tools import FileInfo, SystemOverview, generate_system_overview, print_system_overview

__all__ = [
    "AutonomousFiscalOrchestrationCore",
    "GodTierAIEnterpriseSystem",
    "EliteAIEnterprisePro",
    "deploy_elite_enterprise_system",
    "FileInfo",
    "SystemOverview",
    "generate_system_overview",
    "print_system_overview",
]

_TOOLS_EXPORTS = {
    "FileInfo",
    "SystemOverview",
    "generate_system_overview",
    "print_system_overview",
}


def __getattr__(name: str) -> Any:
    if name in _TOOLS_EXPORTS:
        module = import_module(".tools", __name__)
        attr = getattr(module, name)
        globals()[name] = attr
        return attr
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
