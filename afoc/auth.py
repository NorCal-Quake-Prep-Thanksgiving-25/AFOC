"""Simple API key authentication helpers for the AFOC surfaces."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class APIAuthConfig:
    """Configuration describing how API key authentication should behave."""

    api_key: Optional[str]
    header_name: str = "X-API-Key"

    @classmethod
    def from_env(cls) -> "APIAuthConfig":
        """Build a config from environment variables."""

        return cls(api_key=os.getenv("AFOC_API_KEY"))

    def verify(self, candidate: Optional[str]) -> bool:
        """Return True when authentication passes.

        If no API key is configured the guard runs in permissive mode so that
        local demos and notebooks continue to function without additional
        configuration.
        """

        if not self.api_key:
            return True
        return bool(candidate) and candidate == self.api_key


class APIAuthError(RuntimeError):
    """Raised when authentication fails outside of the FastAPI context."""


def enforce_api_key(config: APIAuthConfig, candidate: Optional[str]) -> None:
    """Raise an :class:`APIAuthError` when the supplied key is invalid."""

    if not config.verify(candidate):
        raise APIAuthError("Invalid or missing API key")
