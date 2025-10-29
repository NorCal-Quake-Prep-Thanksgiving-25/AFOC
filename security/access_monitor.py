"""Repository access monitoring utilities."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Sequence


@dataclass
class AccessEvent:
    """Captures repository access activity."""

    actor: str
    action: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, str] = field(default_factory=dict)


class RepositoryAccessMonitor:
    """In-memory monitor that records repository interactions."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self._events: List[AccessEvent] = []

    def record_event(self, actor: str, action: str, **metadata: str) -> None:
        event = AccessEvent(actor=actor, action=action, metadata=metadata)
        self._events.append(event)
        self.logger.debug("Recorded access event: %s", event)

    def recent_events(self, limit: int = 20) -> Sequence[AccessEvent]:
        return self._events[-limit:]

    def summarise(self) -> dict[str, int]:
        summary: dict[str, int] = {}
        for event in self._events:
            summary[event.action] = summary.get(event.action, 0) + 1
        return summary

