"""Pre-push security scanning pipeline."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

from afoc.datatypes import ProtectionReport, SecurityScan

from .code_protector import CommercialCodeProtector
from .commercial_ip_guard import CommercialIPGuard
from .legal_guard import LegalProtectionAutomation
from .secret_scanner import SecretScanner


class PrePushSecurityScanner:
    """Runs before every git push to ensure security."""

    def __init__(self, repo_root: str | Path = Path(".")) -> None:
        self.repo_root = Path(repo_root)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.secret_scanner = SecretScanner(self.repo_root)
        self.ip_guard = CommercialIPGuard(self.repo_root)
        self.legal_automation = LegalProtectionAutomation()
        self.protector = CommercialCodeProtector(self.repo_root)

    def scan_for_vulnerabilities(self) -> SecurityScan:
        secrets = self.secret_scanner.scan_for_secrets()
        leaks = self.ip_guard.detect_ip_leakage()
        protection_report = self.protector.protect_eliteai_system(modules=("core",))
        legal_headers_present = bool(protection_report.legal_headers)
        scan = SecurityScan(
            secrets_detected=secrets,
            ip_exposure=leaks,
            obfuscation_status=bool(protection_report.obfuscated_modules),
            legal_headers=legal_headers_present,
        )
        self.logger.info("Security scan completed: secure=%s", scan.all_secure)
        return scan

    def auto_fix_issues(self) -> ProtectionReport:
        self.logger.warning("Auto-fix triggered for security issues.")
        modules_to_protect: Sequence[str] = (
            "core",
            "quantum_roi_engine",
            "elite_enterprise",
        )
        report = self.protector.protect_eliteai_system(modules=modules_to_protect)
        self.logger.info("Auto-fix applied with report: %s", report.summary())
        return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scanner = PrePushSecurityScanner()
    result = scanner.scan_for_vulnerabilities()
    print(f"All secure: {result.all_secure}")
    if not result.all_secure:
        scanner.auto_fix_issues()

