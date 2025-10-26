"""Autonomous Fiscal Orchestration Core package."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

from .core import AutonomousFiscalOrchestrationCore, ComposableIntelligenceCore
from .api import build_api
from .graphql import build_graphql_router
from .data import DataFabric, DataFabricConfig, IngestionReport
from .cli import main as cli_main
from .elite_enterprise import EliteAIEnterprisePro, deploy_elite_enterprise_system
from .dashboard import launch_streamlit_dashboard
from .models import GodTierAIEnterpriseSystem
from .logging import configure_logging, get_logger
from .intelligence import QuantumOptimizer
from .datatypes import QuantumOptimizationSummary
from .credentials import (
    CredentialProvider,
    CompositeCredentialProvider,
    EnvironmentCredentialProvider,
    KeyringCredentialProvider,
    default_credential_provider,
)

if TYPE_CHECKING:  # pragma: no cover - import for static analysis only
    from .tools import (
        FileInfo,
        FilePreview,
        SystemOverview,
        generate_preview_view,
        generate_system_overview,
        print_preview_view,
        print_system_overview,
        export_pdf_summary,
    )

__all__ = [
    "AutonomousFiscalOrchestrationCore",
    "ComposableIntelligenceCore",
    "GodTierAIEnterpriseSystem",
    "EliteAIEnterprisePro",
    "deploy_elite_enterprise_system",
    "launch_streamlit_dashboard",
    "build_api",
    "build_graphql_router",
    "DataFabric",
    "DataFabricConfig",
    "IngestionReport",
    "cli_main",
    "configure_logging",
    "get_logger",
    "QuantumOptimizer",
    "QuantumOptimizationSummary",
    "CredentialProvider",
    "CompositeCredentialProvider",
    "EnvironmentCredentialProvider",
    "KeyringCredentialProvider",
    "default_credential_provider",
    "FileInfo",
    "FilePreview",
    "SystemOverview",
    "generate_preview_view",
    "generate_system_overview",
    "print_preview_view",
    "print_system_overview",
    "export_pdf_summary",
]

_TOOLS_EXPORTS = {
    "FileInfo",
    "FilePreview",
    "SystemOverview",
    "generate_preview_view",
    "generate_system_overview",
    "print_preview_view",
    "print_system_overview",
    "export_pdf_summary",
}


def __getattr__(name: str) -> Any:
    if name in _TOOLS_EXPORTS:
        module = import_module(".tools", __name__)
        attr = getattr(module, name)
        globals()[name] = attr
        return attr
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
