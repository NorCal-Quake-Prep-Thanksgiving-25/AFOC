"""Credential resolution utilities for the AFOC platform."""

from __future__ import annotations

import os
import base64
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


class KMSCipherCredentialProvider:
    """Decrypts secrets stored in cloud KMS ciphertexts."""

    def __init__(self) -> None:
        self._gcp_key_name = os.getenv("AFOC_KMS_GCP_KEY")
        self._aws_key_id = os.getenv("AFOC_KMS_AWS_KEY_ID")
        try:  # pragma: no cover - optional dependency
            from google.cloud import kms  # type: ignore

            self._gcp_client = kms.KeyManagementServiceClient()
        except Exception:
            self._gcp_client = None
        try:  # pragma: no cover - optional dependency
            import boto3  # type: ignore

            self._aws_client = boto3.client("kms")
        except Exception:
            self._aws_client = None
        try:  # pragma: no cover - optional dependency
            from cryptography.fernet import Fernet  # type: ignore

            self._fernet_cls = Fernet
        except Exception:
            self._fernet_cls = None
        local_key = os.getenv("AFOC_KMS_LOCAL_KEY")
        self._local_key = local_key.encode("utf-8") if local_key else None

    def get_secret(self, name: str) -> Optional[str]:
        ciphertext = os.getenv(f"AFOC_KMS_{name.upper()}")
        if not ciphertext:
            return None
        decoded: bytes | None = None
        try:
            decoded = base64.b64decode(ciphertext)
        except Exception:
            decoded = None
        if self._gcp_client and self._gcp_key_name and decoded is not None:
            try:  # pragma: no cover - optional dependency
                response = self._gcp_client.decrypt(
                    request={"name": self._gcp_key_name, "ciphertext": decoded}
                )
                return response.plaintext.decode("utf-8")
            except Exception:
                pass
        if self._aws_client and self._aws_key_id and decoded is not None:
            try:  # pragma: no cover - optional dependency
                response = self._aws_client.decrypt(  # type: ignore[attr-defined]
                    CiphertextBlob=decoded, KeyId=self._aws_key_id
                )
                plaintext = response.get("Plaintext")
                if isinstance(plaintext, (bytes, bytearray)):
                    return plaintext.decode("utf-8")
            except Exception:
                pass
        if self._fernet_cls and self._local_key:
            try:
                fernet = self._fernet_cls(self._local_key)
                return fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
            except Exception:
                return None
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
    providers=(
        KMSCipherCredentialProvider(),
        EnvironmentCredentialProvider(),
        KeyringCredentialProvider(),
    )
)
