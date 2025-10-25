"""Commercial intellectual property protection blueprint."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass
class CommercialIPGuard:
    """Defines the multi-layer commercial IP protection strategy."""

    value: str = "$25,000,000"
    protection_measures: Sequence[str] = field(
        default_factory=lambda: (
            "Digital watermarking in all algorithms",
            "Legal takedown automation",
            "Competitive intelligence monitoring",
            "Automatic copyright registration",
        )
    )

    def summary(self) -> str:
        measures = ", ".join(self.protection_measures)
        return f"CommercialIPGuard(value={self.value}, measures=[{measures}])"

    def generate_playbook(self) -> dict[str, Sequence[str]]:
        """Return a structured view of protection measures by layer."""

        return {
            "legal": (self.protection_measures[1], self.protection_measures[3]),
            "technical": (self.protection_measures[0],),
            "intelligence": (self.protection_measures[2],),
        }
