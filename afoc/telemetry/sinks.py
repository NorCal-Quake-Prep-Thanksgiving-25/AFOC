"""Telemetry sinks for streaming events into different stores."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .bus import publish
from .events import BaseEvent


def db_sink(event: BaseEvent) -> None:
    """Persist an event using the default bus."""

    publish(event)


def file_sink(event: BaseEvent, path: str | Path) -> None:
    """Append an event to a newline-delimited JSON file."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event.model_dump(), default=str))
        handle.write("\n")


def stdout_sink(event: BaseEvent) -> None:
    """Print the event for debugging sessions."""

    print(json.dumps(event.model_dump(), default=str))


def drain(events: Iterable[BaseEvent], sink=db_sink) -> None:
    """Push a batch of events into the provided sink."""

    for event in events:
        sink(event)


__all__ = ["db_sink", "file_sink", "stdout_sink", "drain"]
