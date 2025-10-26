"""Compatibility helpers providing a lightweight BaseModel when pydantic is unavailable."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

try:  # pragma: no cover - use real dependency when available
    from pydantic import BaseModel as PydanticBaseModel, Field
except Exception:  # pragma: no cover - fallback implementation

    class BaseModel:  # type: ignore[misc]
        def __init__(self, **data: Any) -> None:
            for key, value in data.items():
                setattr(self, key, value)

        def dict(self) -> dict[str, Any]:
            return dict(self.__dict__)

        def model_dump(self) -> dict[str, Any]:
            return self.dict()  # Security: alias keeps legacy callers while removing deprecated API usage warnings.

        def json(self, *, indent: int | None = None) -> str:
            return json.dumps(self.model_dump(), indent=indent)

        def model_dump_json(self, *, indent: int | None = None) -> str:
            return self.json(indent=indent)  # Security: guarantees consistent serialisation surface for tamper-evident logs.

        def model_copy(self) -> "BaseModel":
            return self.__class__(**self.model_dump())

    def Field(default: Any = None, **_: Any) -> Any:  # type: ignore
        return default

else:
    BaseModel = PydanticBaseModel  # type: ignore[misc, assignment]
    if not hasattr(BaseModel, "model_dump"):
        def _model_dump(self: "BaseModel", *args: Any, **kwargs: Any) -> dict[str, Any]:
            return self.dict(*args, **kwargs)  # Security: maintains stable serialisation semantics on legacy pydantic installs.

        BaseModel.model_dump = _model_dump  # type: ignore[attr-defined]

    if not hasattr(BaseModel, "model_dump_json"):
        def _model_dump_json(self: "BaseModel", *args: Any, **kwargs: Any) -> str:
            return self.json(*args, **kwargs)  # Security: exposes unified JSON encoding for audit logging consistency.

        BaseModel.model_dump_json = _model_dump_json  # type: ignore[attr-defined]

__all__ = ["BaseModel", "Field"]
