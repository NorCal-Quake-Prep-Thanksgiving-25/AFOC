"""Utility helpers for orchestrating AFOC workflows."""

from typing import Any


def noop(value: Any) -> Any:
    """Return the provided value without modification."""

    return value
