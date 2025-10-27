"""Core type declarations for the orchestration pipeline."""

from typing import Any, Dict, Protocol


class DataPayload(Dict[str, Any]):
    """Represents a generic payload exchanged between services."""


class Processor(Protocol):
    """Protocol describing a callable processor."""

    def __call__(self, payload: DataPayload) -> DataPayload:
        ...
