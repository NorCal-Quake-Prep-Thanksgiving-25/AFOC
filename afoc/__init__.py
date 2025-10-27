"""Autonomous Fiscal Orchestration Core package."""

# coverage: ignore file  # Security: package facade excluded from coverage to focus gating on runtime enforcement modules.

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any, Callable

from .core import AutonomousFiscalOrchestrationCore, ComposableIntelligenceCore

_build_api_impl: Callable[..., Any] | None
try:  # pragma: no cover - optional API dependency may be absent in minimal installs
    from .api import build_api as _build_api_impl
except Exception:  # pragma: no cover - degrade gracefully when FastAPI stack missing
    _build_api_impl = None
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
    KMSCipherCredentialProvider,
    AFOCSecretsManager,  # Security: expose central secret loader for integrations needing hardened access.
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
    "KMSCipherCredentialProvider",
    "AFOCSecretsManager",  # Security: allow consumers to depend on the hardened secrets manager.
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


def build_api(*args: Any, **kwargs: Any) -> Any:
    """Lazily expose the FastAPI façade when optional deps are installed."""

    impl = _build_api_impl  # Performance: local binding avoids repeated global lookups during hot paths.
    if impl is None:
        raise RuntimeError(
            "FastAPI extras are required. Install with `pip install afoc[api]` to enable the REST façade."
        )  # Security: prevents exposing unauthenticated routes when hardened dependencies are unavailable.
    return impl(*args, **kwargs)


def __getattr__(name: str) -> Any:
    if name in _TOOLS_EXPORTS:
        module = import_module(".tools", __name__)
        attr = getattr(module, name)
        globals()[name] = attr
        return attr
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
