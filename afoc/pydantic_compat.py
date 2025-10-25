"""Compatibility helpers providing a lightweight BaseModel when pydantic is unavailable."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

try:  # pragma: no cover - use real dependency when available
    from pydantic import BaseModel, Field  # type: ignore
except Exception:  # pragma: no cover - fallback implementation

    class BaseModel:  # type: ignore[misc]
        def __init__(self, **data: Any) -> None:
            for key, value in data.items():
                setattr(self, key, value)

        def dict(self) -> dict[str, Any]:
            return dict(self.__dict__)

        def json(self, *, indent: int | None = None) -> str:
            return json.dumps(self.dict(), indent=indent)

        def model_copy(self) -> "BaseModel":
            return self.__class__(**self.dict())

    def Field(default: Any = None, **_: Any) -> Any:  # type: ignore
        return default

__all__ = ["BaseModel", "Field"]
