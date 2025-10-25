"""Credential resolution utilities for the AFOC platform."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, Optional, Protocol


class CredentialProvider(Protocol):
    """Simplified protocol for retrieving named secrets."""

    def get_secret(self, name: str) -> Optional[str]:
        """Return the secret value if available."""


@dataclass
class EnvironmentCredentialProvider:
    """Loads secrets from environment variables with a configurable prefix."""

    prefix: str = "AFOC_"

    def get_secret(self, name: str) -> Optional[str]:
        key = f"{self.prefix}{name.upper()}"
        return os.getenv(key)


class KeyringCredentialProvider:
    """Optional keyring-backed provider."""

    def __init__(self, service_name: str = "afoc") -> None:
        self._service_name = service_name
        try:  # pragma: no cover - optional dependency
            import keyring

            self._backend = keyring
        except Exception:  # pragma: no cover - fallback when keyring unavailable
            self._backend = None

    def get_secret(self, name: str) -> Optional[str]:
        if self._backend is None:
            return None
        try:  # pragma: no cover - optional dependency
            return self._backend.get_password(self._service_name, name)
        except Exception:
            return None


class CompositeCredentialProvider:
    """Chains multiple providers until a secret is found."""

    def __init__(self, providers: Iterable[CredentialProvider]) -> None:
        self._providers = list(providers)

    def get_secret(self, name: str) -> Optional[str]:
        for provider in self._providers:
            value = provider.get_secret(name)
            if value:
                return value
        return None


default_credential_provider = CompositeCredentialProvider(
    providers=(EnvironmentCredentialProvider(), KeyringCredentialProvider())
)
