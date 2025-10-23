"""Zero-trust repository monitoring utilities."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict


@dataclass
class RepositoryMonitor:
    """Aggregate access telemetry for the EliteAI repository."""

    clone_monitoring: str = "Alert on unexpected clones"
    fork_detection: str = "Private repository – forks disabled"
    access_logging: str = "Log all repository accesses"
    ip_tracking: str = "Track geographic access patterns"
    events: Dict[str, int] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def record_event(self, event: str) -> None:
        self.events[event] = self.events.get(event, 0) + 1

    def detect_unauthorised_access(self) -> dict[str, str]:
        """Return the current zero-trust monitoring configuration."""

        return {
            "clone_monitoring": self.clone_monitoring,
            "fork_detection": self.fork_detection,
            "access_logging": self.access_logging,
            "ip_tracking": self.ip_tracking,
            "events_recorded": str(sum(self.events.values())),
        }
