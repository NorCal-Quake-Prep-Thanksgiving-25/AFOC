"""LLM billing integrations with graceful degradation for offline environments."""

from __future__ import annotations

import os
from random import SystemRandom  # Security: SystemRandom provides secure jitter for API backoff.
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Dict, Optional

import logging

try:  # pragma: no cover - optional dependency
    import httpx
except Exception:  # pragma: no cover - fallback when httpx is unavailable
    httpx = None  # type: ignore

LOGGER = logging.getLogger(__name__)

_LLM_RANDOM = SystemRandom()  # Security: shared entropy source for rate-limit jitter.


class LLMIntegrationError(RuntimeError):
    """Raised when a provider API call fails."""


@dataclass
class LLMUsage:
    provider: str
    model: str
    tokens: int
    cost_usd: float
    window_start: datetime
    window_end: datetime


class LLMUsageCollector:
    """Base collector for LLM billing APIs."""

    provider: str
    api_key_env: str

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        max_attempts: int = 4,
        initial_backoff: float = 0.5,
    ) -> None:
        self.api_key = api_key or os.getenv(self.api_key_env)
        self.max_attempts = max(1, max_attempts)
        self.initial_backoff = max(0.0, initial_backoff)

    def fetch_usage(self) -> LLMUsage:
        start = datetime.now(UTC) - timedelta(days=30)
        end = datetime.now(UTC)
        try:
            tokens, cost = self._fetch_tokens_and_cost(start=start, end=end)
            return LLMUsage(
                provider=self.provider,
                model=self.default_model,
                tokens=tokens,
                cost_usd=cost,
                window_start=start,
                window_end=end,
            )
        except Exception as exc:  # pragma: no cover - network failure, missing deps
            LOGGER.warning("Falling back to synthetic usage for %s: %s", self.provider, exc)
            return LLMUsage(
                provider=self.provider,
                model=self.default_model,
                tokens=180_000,
                cost_usd=480.0,
                window_start=start,
                window_end=end,
            )

    # ------------------------------------------------------------------
    # Provider-specific implementations override this hook
    # ------------------------------------------------------------------
    default_model: str = ""

    def _fetch_tokens_and_cost(
        self, *, start: datetime, end: datetime
    ) -> tuple[int, float]:  # pragma: no cover - interface
        raise NotImplementedError

    def _request_with_backoff(
        self,
        *,
        url: str,
        headers: Dict[str, str],
        params: Dict[str, str],
        label: str,
    ) -> "httpx.Response":
        if httpx is None:
            raise LLMIntegrationError("httpx client is unavailable")
        attempts = 0
        delay = self.initial_backoff
        last_exc: Exception | None = None
        while attempts < self.max_attempts:
            attempts += 1
            try:
                with httpx.Client(timeout=15) as client:
                    response = client.get(url, headers=headers, params=params)
                    response.raise_for_status()
                    return response
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                status = exc.response.status_code
                if status not in {429, 500, 502, 503, 504} or attempts >= self.max_attempts:
                    raise LLMIntegrationError(f"{label} failed with status {status}") from exc
            except httpx.RequestError as exc:
                last_exc = exc
                if attempts >= self.max_attempts:
                    raise LLMIntegrationError(f"{label} request error: {exc}") from exc
            if delay:
                jitter = _LLM_RANDOM.uniform(0, delay / 2)
                time.sleep(delay + jitter)
                delay = delay * 2 if delay else 1.0
        raise LLMIntegrationError(f"{label} failed after retries") from last_exc


class OpenAIUsageCollector(LLMUsageCollector):
    provider = "openai"
    api_key_env = "OPENAI_API_KEY"
    default_model = "gpt-4o"

    def _fetch_tokens_and_cost(
        self, *, start: datetime, end: datetime
    ) -> tuple[int, float]:  # pragma: no cover - optional
        if httpx is None:
            raise LLMIntegrationError("httpx is required for OpenAI usage collection")
        if not self.api_key:
            raise LLMIntegrationError("OPENAI_API_KEY is not configured")
        url = "https://api.openai.com/v1/usage"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {"date": start.date().isoformat(), "end_date": end.date().isoformat()}
        response = self._request_with_backoff(
            url=url,
            headers=headers,
            params=params,
            label="openai_usage",
        )
        payload = response.json()
        # The usage API returns daily aggregates
        total_tokens = int(payload.get("total_usage", {}).get("total_tokens", 0))
        total_cost = float(payload.get("total_usage", {}).get("total_cost", 0.0))
        if total_tokens == 0 and total_cost == 0.0:
            raise LLMIntegrationError("OpenAI usage endpoint returned no data")
        return total_tokens, total_cost


class AnthropicUsageCollector(LLMUsageCollector):
    provider = "anthropic"
    api_key_env = "ANTHROPIC_API_KEY"
    default_model = "claude-3-opus"

    def _fetch_tokens_and_cost(
        self, *, start: datetime, end: datetime
    ) -> tuple[int, float]:  # pragma: no cover - optional
        if httpx is None:
            raise LLMIntegrationError("httpx is required for Anthropic usage collection")
        if not self.api_key:
            raise LLMIntegrationError("ANTHROPIC_API_KEY is not configured")
        url = "https://api.anthropic.com/v1/usage"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        params = {
            "start_date": start.date().isoformat(),
            "end_date": end.date().isoformat(),
        }
        payload = self._request_with_backoff(
            url=url,
            headers=headers,
            params=params,
            label="anthropic_usage",
        ).json()
        totals = payload.get("data", [{}])[-1]
        tokens = int(totals.get("input_tokens", 0) + totals.get("output_tokens", 0))
        cost = float(totals.get("total_cost", 0.0))
        if tokens == 0 and cost == 0.0:
            raise LLMIntegrationError("Anthropic usage endpoint returned no data")
        return tokens, cost


AVAILABLE_USAGE_COLLECTORS: Dict[str, type[LLMUsageCollector]] = {
    "openai": OpenAIUsageCollector,
    "anthropic": AnthropicUsageCollector,
}
