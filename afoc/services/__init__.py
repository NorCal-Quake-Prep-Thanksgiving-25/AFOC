"""Service layer exports with lazy loading."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "anomalies",
    "aggregator",
    "forecasting",
    "rightsizing",
    "valuation",
]


def __getattr__(name: str) -> Any:
    if name in __all__:
        return import_module(f"afoc.services.{name}")
    raise AttributeError(f"module 'afoc.services' has no attribute {name!r}")
