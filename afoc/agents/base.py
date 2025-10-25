"""Protocols and base data structures for agents."""
from __future__ import annotations

from abc import abstractmethod
from typing import Any, Protocol

from ..pydantic_compat import BaseModel


class AllocationProtocol(Protocol):
    """Contract for budget allocation agents."""

    @abstractmethod
    async def allocate(self, request: BaseModel) -> BaseModel:
        raise NotImplementedError


class ForecastProtocol(Protocol):
    """Contract for forecasting agents."""

    @abstractmethod
    async def forecast(self, request: BaseModel) -> BaseModel:
        raise NotImplementedError


class OptimizationProtocol(Protocol):
    """Contract for optimization agents."""

    @abstractmethod
    async def optimize(self, request: BaseModel) -> BaseModel:
        raise NotImplementedError


class SecurityProtocol(Protocol):
    """Contract for runtime security guardians."""

    @abstractmethod
    async def audit(self, context: BaseModel | None = None) -> BaseModel:
        raise NotImplementedError


class SupportsEventBinding(Protocol):
    """Optional protocol for subscribing to the event bus."""

    def bind_event_bus(self, event_bus: Any) -> None:
        raise NotImplementedError
