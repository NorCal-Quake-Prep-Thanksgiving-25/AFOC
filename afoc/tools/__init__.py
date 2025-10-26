"""Utility helpers for inspecting the EliteAI codebase."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - import only for typing
    from .overview import (
        FileInfo,
        FilePreview,
        SystemOverview,
        generate_preview_view,
        generate_system_overview,
        print_preview_view,
        print_system_overview,
    )
    from .reporting import export_pdf_summary

__all__ = [
    "FileInfo",
    "FilePreview",
    "SystemOverview",
    "generate_preview_view",
    "generate_system_overview",
    "print_preview_view",
    "print_system_overview",
    "export_pdf_summary",
]


def __getattr__(name: str) -> Any:
    if name in {"export_pdf_summary"}:
        module = import_module(".reporting", __name__)
        attr = getattr(module, name)
        return attr
    if name in __all__:
        module = import_module(".overview", __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
