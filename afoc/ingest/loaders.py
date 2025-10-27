"""Placeholder ingestion logic for bootstrap phase."""

from typing import List


def load_placeholder_dataset() -> List[dict]:
    """Return a dummy dataset representing ingested usage events."""

    return [{"id": 1, "value": 0.0}]
