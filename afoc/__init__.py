"""Autonomous Fiscal Orchestration Core package."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import FastAPI

__all__ = ["create_app", "Agent", "TelemetryStore", "AdaptiveController"]


def create_app() -> "FastAPI":
    """Return the FastAPI application factory lazily."""

    from .api.app import create_app as _create_app

    return _create_app()


def __getattr__(name: str) -> Any:
    if name == "Agent":
        try:
            module = import_module("afoc.orchestrator")
        except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "orchestrator requires SQLAlchemy; install optional dependencies"
            ) from exc
        return module.Agent
    if name in {"TelemetryStore", "AdaptiveController"}:
        try:
            module = import_module("afoc.telemetry")
        except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "telemetry requires SQLAlchemy; install optional dependencies"
            ) from exc
        return getattr(module, name)
    raise AttributeError(name)
