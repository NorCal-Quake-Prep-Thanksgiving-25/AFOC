"""Authentication and rate limiting utilities for the API layer."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Deque, DefaultDict

from fastapi import Depends, Header, HTTPException, Request, status

from ..config import settings


@dataclass
class AuthContext:
    """Minimal authentication context returned to route handlers."""

    token: str
    role: str

    @property
    def rate_limit_key(self) -> str:
        """Return the cache key used for rate limiting buckets."""

        return f"{self.token}:{self.role}"


class SlidingWindowRateLimiter:
    """Simple in-memory rate limiter using a sliding time window."""

    def __init__(self, limit: int, window_seconds: float = 60.0) -> None:
        self._limit = limit
        self._window = window_seconds
        self._lock = Lock()
        self._hits: DefaultDict[str, Deque[float]] = defaultdict(deque)

    @property
    def limit(self) -> int:
        """Expose the configured limit for dynamic reconfiguration."""

        return self._limit

    def check(self, key: str) -> None:
        """Register a request and raise if the window is saturated."""

        now = monotonic()
        with self._lock:
            history = self._hits[key]
            while history and now - history[0] > self._window:
                history.popleft()
            if len(history) >= self._limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                )
            history.append(now)


_limiter: SlidingWindowRateLimiter | None = None
_limiter_lock = Lock()


def get_rate_limiter() -> SlidingWindowRateLimiter:
    """Return a limiter instance aligned with the current configuration."""

    global _limiter
    with _limiter_lock:
        if _limiter is None or _limiter.limit != settings.api_rate_limit_per_minute:
            _limiter = SlidingWindowRateLimiter(settings.api_rate_limit_per_minute)
        return _limiter


def authenticate(
    x_api_key: str | None = Header(None, alias="X-API-Key")
) -> AuthContext:
    """Validate the provided API key against configured tokens."""

    tokens = getattr(settings, "api_tokens", ("dev-token",))
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        )
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )
    provided_token, _, provided_role = x_api_key.partition(":")
    for entry in tokens:
        stored_token, _, stored_role = entry.partition(":")
        if stored_token == provided_token:
            role = provided_role or stored_role or "viewer"
            return AuthContext(token=stored_token, role=role)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
    )


def enforce_security(
    request: Request, context: AuthContext = Depends(authenticate)
) -> AuthContext:
    """Apply rate limiting and return the resolved auth context."""

    limiter = get_rate_limiter()
    client_host = request.client.host if request.client else "anonymous"
    limiter_key = f"{context.rate_limit_key}:{client_host}"
    limiter.check(limiter_key)
    return context
