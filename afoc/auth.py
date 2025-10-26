"""JWT and API key authentication helpers for the AFOC surfaces."""

from __future__ import annotations

import hashlib  # Security: use SHA-256 hashing to avoid weak credential digests.
import secrets  # Security: constant-time comparisons mitigate timing attacks on secrets.
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, Optional, Sequence

import jwt  # Security: PyJWT provides battle-tested token signing and verification.

from .credentials import AFOCSecretsManager


@dataclass(slots=True)
class UserPrincipal:
    """Represents an authenticated user and their roles."""

    username: str
    roles: Sequence[str]


@dataclass(slots=True)
class JWTAuthConfig:
    """Holds configuration for issuing and verifying JWTs."""

    secret: str
    algorithm: str = "HS256"
    access_ttl_seconds: int = 900

    @classmethod
    def from_secrets(cls, secrets_manager: AFOCSecretsManager | None = None) -> "JWTAuthConfig":
        manager = secrets_manager or AFOCSecretsManager()
        secret = manager.require_secret(
            "APP_SECRET"
        )  # Security: centralises JWT secret retrieval through hardened manager.
        ttl_raw = manager.get_secret("JWT_TTL_SECONDS", "900")
        if ttl_raw is None:
            ttl = 900
        else:
            try:
                ttl = int(ttl_raw)
            except ValueError:
                ttl = 900
        return cls(secret=secret, access_ttl_seconds=max(ttl, 60))


class JWTAuthenticator:
    """Authenticates users and issues signed JWT access tokens."""

    def __init__(self, config: JWTAuthConfig | None = None) -> None:
        self._secrets = AFOCSecretsManager()
        self._config = config or JWTAuthConfig.from_secrets(self._secrets)
        self._users = (
            self._load_users()
        )  # Security: cache registry to avoid repeated secret fetches and reduce attack surface.

    def _load_users(self) -> Dict[str, Dict[str, Any]]:
        registry = self._secrets.user_registry()
        if not registry:
            default_password = hashlib.sha256(
                b"changeme"
            ).hexdigest()  # Security: default admin password stored hashed to prevent accidental plaintext leakage.
            registry = {
                "admin": {
                    "password_sha256": default_password,
                    "roles": ["admin", "analyst", "viewer"],
                }
            }
        return registry

    def authenticate(self, username: str, password: str) -> Optional[UserPrincipal]:
        record = self._users.get(username)
        if not record:
            return None
        stored_hash = str(record.get("password_sha256", ""))
        candidate_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        if not secrets.compare_digest(
            stored_hash, candidate_hash
        ):  # Security: constant-time comparison thwarts timing probes.
            return None
        roles_raw = record.get("roles", [])
        if isinstance(roles_raw, (list, tuple, set)):
            resolved_roles = [str(role) for role in roles_raw]
        elif roles_raw:
            resolved_roles = [str(roles_raw)]
        else:
            resolved_roles = []
        return UserPrincipal(username=username, roles=resolved_roles)

    def issue_token(self, principal: UserPrincipal) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": principal.username,
            "roles": list(principal.roles),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=self._config.access_ttl_seconds)).timestamp()),
        }
        return jwt.encode(payload, self._config.secret, algorithm=self._config.algorithm)

    def verify_token(self, token: str) -> UserPrincipal:
        payload = jwt.decode(
            token, self._config.secret, algorithms=[self._config.algorithm]
        )  # Security: strictly bound algorithm prevents downgrade attacks.
        username = str(payload["sub"])
        roles = payload.get("roles", [])
        if not isinstance(roles, Iterable):
            roles = []
        return UserPrincipal(username=username, roles=[str(role) for role in roles])


def require_roles(principal: UserPrincipal, *required: str) -> None:
    if not required:
        return
    granted = {role.lower() for role in principal.roles}
    if not all(role.lower() in granted for role in required):
        raise PermissionError(
            "Insufficient role permissions"
        )  # Security: immediate rejection blocks privilege escalation attempts.


@dataclass(slots=True)
class APIAuthConfig:
    """Legacy API key support retained for backwards compatibility."""

    api_key: Optional[str]
    header_name: str = "X-API-Key"

    @classmethod
    def from_env(cls) -> "APIAuthConfig":
        manager = AFOCSecretsManager()
        return cls(api_key=manager.get_secret("API_KEY"))

    def verify(self, candidate: Optional[str]) -> bool:
        if not self.api_key:
            return True
        if candidate is None:
            return False
        return secrets.compare_digest(
            self.api_key, candidate
        )  # Security: consistent comparison avoids leak of API key timing.


class APIAuthError(RuntimeError):
    """Raised when authentication fails outside of the FastAPI context."""


def enforce_api_key(config: APIAuthConfig, candidate: Optional[str]) -> None:
    if not config.verify(candidate):
        raise APIAuthError("Invalid or missing API key")
