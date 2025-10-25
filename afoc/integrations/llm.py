"""LLM cost and usage collectors."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class LLMUsage:
    provider: str
    model: str
    tokens: int
    cost_usd: float


class LLMUsageCollector:
    """Base collector for LLM billing APIs."""

    provider: str

    def fetch_usage(self) -> LLMUsage:
        raise NotImplementedError


class OpenAIUsageCollector(LLMUsageCollector):
    provider = "openai"

    def fetch_usage(self) -> LLMUsage:
        # Placeholder with synthetic usage metrics
        return LLMUsage(provider=self.provider, model="gpt-4-turbo", tokens=150000, cost_usd=450.0)


class AnthropicUsageCollector(LLMUsageCollector):
    provider = "anthropic"

    def fetch_usage(self) -> LLMUsage:
        return LLMUsage(provider=self.provider, model="claude-3-opus", tokens=120000, cost_usd=360.0)


AVAILABLE_USAGE_COLLECTORS: Dict[str, type[LLMUsageCollector]] = {
    "openai": OpenAIUsageCollector,
    "anthropic": AnthropicUsageCollector,
}
