"""Lightweight async event bus shared by the agents."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from typing import Awaitable, Callable, DefaultDict, List, Optional

from ..pydantic_compat import BaseModel


class AgentEvent(BaseModel):
    """Represents a message dispatched between agents."""

    type: str
    payload: dict


EventHandler = Callable[[AgentEvent], Awaitable[None]]


@dataclass
class EventBusMetrics:
    """Runtime metrics captured for observability."""

    published: int = 0
    delivered: int = 0
    subscribers: int = 0
    avg_latency: float = 0.0
    max_latency: float = 0.0
    last_event_type: Optional[str] = None


class AsyncEventBus:
    """Asyncio-powered pub/sub bus for coordinating agents."""

    def __init__(self) -> None:
        self._subscribers: DefaultDict[str, List[EventHandler]] = defaultdict(list)
        self._metrics = EventBusMetrics()
        try:
            self._loop = asyncio.get_event_loop()
        except RuntimeError:  # pragma: no cover - fallback for new threads
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._subscribers[event_type].append(handler)
        self._metrics.subscribers = sum(len(items) for items in self._subscribers.values())

    async def publish(self, event: AgentEvent) -> None:
        handlers = list(self._subscribers.get(event.type, ()))
        if not handlers:
            return
        self._metrics.published += 1
        self._metrics.delivered += len(handlers)
        start = self._loop.time()
        await asyncio.gather(*(handler(event) for handler in handlers))
        latency = max(self._loop.time() - start, 0.0)
        total_latency = self._metrics.avg_latency * (self._metrics.published - 1) + latency
        self._metrics.avg_latency = total_latency / max(self._metrics.published, 1)
        self._metrics.max_latency = max(self._metrics.max_latency, latency)
        self._metrics.last_event_type = event.type

    def publish_sync(self, event: AgentEvent) -> None:
        """Helper for sync callers."""

        async def _runner() -> None:
            await self.publish(event)

        asyncio.run(_runner())

    def metrics(self) -> EventBusMetrics:
        return EventBusMetrics(
            published=self._metrics.published,
            delivered=self._metrics.delivered,
            subscribers=self._metrics.subscribers,
            avg_latency=self._metrics.avg_latency,
            max_latency=self._metrics.max_latency,
            last_event_type=self._metrics.last_event_type,
        )
