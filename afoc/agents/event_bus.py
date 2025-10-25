"""Lightweight async event bus shared by the agents."""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Awaitable, Callable, DefaultDict, List

from ..pydantic_compat import BaseModel


class AgentEvent(BaseModel):
    """Represents a message dispatched between agents."""

    type: str
    payload: dict


EventHandler = Callable[[AgentEvent], Awaitable[None]]


class AsyncEventBus:
    """Asyncio-powered pub/sub bus for coordinating agents."""

    def __init__(self) -> None:
        self._subscribers: DefaultDict[str, List[EventHandler]] = defaultdict(list)
        try:
            self._loop = asyncio.get_event_loop()
        except RuntimeError:  # pragma: no cover - fallback for new threads
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._subscribers[event_type].append(handler)

    async def publish(self, event: AgentEvent) -> None:
        handlers = list(self._subscribers.get(event.type, ()))
        if not handlers:
            return
        await asyncio.gather(*(handler(event) for handler in handlers))

    def publish_sync(self, event: AgentEvent) -> None:
        """Helper for sync callers."""

        async def _runner() -> None:
            await self.publish(event)

        asyncio.run(_runner())
