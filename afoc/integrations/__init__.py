"""Integration helpers for external platforms."""

from importlib import import_module
from typing import Any

__all__ = ["aws"]


def __getattr__(name: str) -> Any:
    if name in __all__:
        return import_module(f"afoc.integrations.{name}")
    raise AttributeError(f"module 'afoc.integrations' has no attribute {name!r}")
