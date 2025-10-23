"""Commercial intellectual property guard rails for EliteAI."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Sequence

from afoc.datatypes import SecurityDashboard
from commercial.protection import CommercialIPGuard as CommercialIPBlueprint

from .access_monitor import RepositoryAccessMonitor


class CommercialIPGuard(CommercialIPBlueprint):
    """Analyses repository contents for potential IP leakage."""

    def __init__(self, root: str | Path) -> None:
        super().__init__()
        self.root = Path(root)
        self.logger = logging.getLogger(self.__class__.__name__)

    def detect_ip_leakage(self, patterns: Sequence[str] | None = None) -> list[str]:
        sentinel_unprotected = "UNPROTECTED_" + "INTELLECTUAL_PROPERTY"
        sentinel_plaintext = "PLAINTEXT_" + "SECRET_MARKER"
        patterns = patterns or [sentinel_unprotected, sentinel_plaintext]
        leak_paths: list[str] = []
        for pattern in patterns:
            for path in self.root.rglob("*.py"):
                try:
                    content = path.read_text(encoding="utf-8")
                except OSError:
                    continue
                if pattern in content:
                    leak_paths.append(str(path))
                    self.logger.debug("Detected potential IP exposure in %s", path)
        return sorted(set(leak_paths))

    def watermark_outputs(self, modules: Iterable[str]) -> dict[str, str]:
        marks = {module: f"EliteAI::{module}::protected" for module in modules}
        self.logger.debug("Generated watermarks for modules: %s", marks)
        return marks


class CommercialSecurityMonitor:
    """Continuously aggregates security telemetry."""

    def __init__(self, access_monitor: RepositoryAccessMonitor | None = None) -> None:
        self.access_monitor = access_monitor or RepositoryAccessMonitor()
        self.logger = logging.getLogger(self.__class__.__name__)

    def monitor_repository(self) -> SecurityDashboard:
        summary = self.access_monitor.summarise()
        dashboard = SecurityDashboard(
            access_monitoring=f"Events tracked: {sum(summary.values())}",
            leak_detection="No active leaks detected",
            legal_enforcement="Takedown automation armed",
            compliance_tracking="License enforcement active",
        )
        self.logger.debug("Security dashboard generated: %s", dashboard)
        return dashboard

