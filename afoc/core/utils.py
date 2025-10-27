"""Utility helpers for orchestrating AFOC workflows."""

from typing import Any


def noop(value: Any) -> Any:
    """Return the provided value without modification."""

    return value


def clamp(value: float, lower: float, upper: float) -> float:
    """Clamp ``value`` between ``lower`` and ``upper`` bounds."""

    if value < lower:
        return lower
    if value > upper:
        return upper
    return value
