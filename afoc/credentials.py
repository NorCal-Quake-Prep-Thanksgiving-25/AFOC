"""Credential resolution utilities for the AFOC platform."""

from __future__ import annotations

import os
import base64
import json  # Security: explicit import enables structured policy parsing without eval risks.
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Protocol

try:  # Security: optional dependency keeps env loading local without breaking deployments.
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - gracefully degrade when python-dotenv absent
    load_dotenv = None


logger = logging.getLogger(
    __name__
)  # Security: shared logger surfaces credential errors without exposing secrets.


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
        except Exception as exc:
            logger.warning("Failed to base64 decode ciphertext", extra={"error": str(exc)})
            decoded = (
                None  # Security: logged failure ensures forensic trail without leaking ciphertext.
            )
        if self._gcp_client and self._gcp_key_name and decoded is not None:
            try:  # pragma: no cover - optional dependency
                response = self._gcp_client.decrypt(
                    request={"name": self._gcp_key_name, "ciphertext": decoded}
                )
                return response.plaintext.decode("utf-8")
            except Exception as exc:
                logger.warning(
                    "GCP KMS decrypt failed", extra={"error": str(exc)}
                )  # Security: emit audit signal before falling back to next provider.
        if self._aws_client and self._aws_key_id and decoded is not None:
            try:  # pragma: no cover - optional dependency
                response = self._aws_client.decrypt(  # type: ignore[attr-defined]
                    CiphertextBlob=decoded, KeyId=self._aws_key_id
                )
                plaintext = response.get("Plaintext")
                if isinstance(plaintext, (bytes, bytearray)):
                    return plaintext.decode("utf-8")
            except Exception as exc:
                logger.warning(
                    "AWS KMS decrypt failed", extra={"error": str(exc)}
                )  # Security: record AWS failure and continue to local fallback.
        if self._fernet_cls and self._local_key:
            try:
                fernet = self._fernet_cls(self._local_key)
                return fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
            except Exception as exc:
                logger.warning(
                    "Local KMS decrypt failed", extra={"error": str(exc)}
                )  # Security: logging protects against silent tampering in local secrets.
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


class AFOCSecretsManager:
    """Centralised secret manager that favours secure sources."""

    def __init__(
        self,
        provider: CredentialProvider | None = None,
        env_file: str | None = ".env",
    ) -> None:
        self._provider = provider or default_credential_provider
        self._loaded_env = False
        self._env_file = Path(env_file) if env_file else None
        if self._env_file and not self._loaded_env:
            if load_dotenv is not None and self._env_file.exists():
                load_dotenv(
                    self._env_file
                )  # Security: ensures .env secrets load without embedding plain text in code.
                self._loaded_env = True

    def get_secret(self, name: str, default: Optional[str] = None) -> Optional[str]:
        value = self._provider.get_secret(name)
        return (
            value if value is not None else default
        )  # Security: explicit default avoids accidental None usage in crypto paths.

    def require_secret(self, name: str) -> str:
        value = self.get_secret(name)
        if value is None:
            raise RuntimeError(
                f"Missing required secret: {name}"
            )  # Security: fail fast stops services from booting without critical secrets.
        return value

    def user_registry(self) -> Dict[str, Dict[str, Any]]:
        raw = self.get_secret("USERS_JSON")
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except (
            json.JSONDecodeError
        ) as exc:  # Security: validate input to avoid malicious injection via malformed JSON.
            raise ValueError("Invalid USERS_JSON secret payload") from exc
        return parsed if isinstance(parsed, dict) else {}
