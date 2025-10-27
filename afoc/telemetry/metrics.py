"""Simple in-memory telemetry metrics."""

from __future__ import annotations

from collections import defaultdict
from threading import Lock
from time import time
from typing import Dict, MutableMapping, Tuple

_COUNTERS: MutableMapping[str, int] = defaultdict(int)
_HISTOGRAMS: MutableMapping[str, list[Tuple[float, float]]] = defaultdict(list)
_LOCK = Lock()


def increment_counter(name: str, value: int = 1) -> None:
    """Increase a counter atomically."""

    with _LOCK:
        _COUNTERS[name] += value


def observe_latency(name: str, duration: float) -> None:
    """Record a latency measurement for histogram reporting."""

    with _LOCK:
        _HISTOGRAMS[name].append((time(), duration))


def snapshot() -> Dict[str, object]:
    """Return a copy of all metrics for diagnostics."""

    with _LOCK:
        return {
            "counters": dict(_COUNTERS),
            "histograms": {
                key: list(values[-50:]) for key, values in _HISTOGRAMS.items()
            },
        }


__all__ = ["increment_counter", "observe_latency", "snapshot"]
