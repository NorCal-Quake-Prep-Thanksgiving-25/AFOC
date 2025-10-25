"""Commercial security audit orchestration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

from afoc.datatypes import RepositoryHardeningReport, SecurityAuditResult

from .code_protector import CommercialCodeProtector
from .git_security import setup_git_security
from .pre_push_scanner import PrePushSecurityScanner
from .setup import CommercialRepositorySetup


class CommercialSecurityAudit:
    """Runs the full DeepSeek-recommended security audit."""

    def __init__(self, repo_root: str | Path = Path(".")) -> None:
        self.repo_root = Path(repo_root)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.scanner = PrePushSecurityScanner(self.repo_root)
        self.code_protector = CommercialCodeProtector(self.repo_root)
        self.setup_helper = CommercialRepositorySetup(self.repo_root)

    def _collect_hardening(self) -> RepositoryHardeningReport:
        return self.setup_helper.harden_github_repository()

    def scan_repository(self) -> SecurityAuditResult:
        """Execute the full audit returning structured findings."""

        hardening_report = self._collect_hardening()
        scan = self.scanner.scan_for_vulnerabilities()
        issues: list[str] = []

        if scan.secrets_detected:
            issues.append(f"Secrets detected in: {', '.join(scan.secrets_detected)}")
        if scan.ip_exposure:
            issues.append(f"Potential IP exposure: {', '.join(scan.ip_exposure)}")
        if not scan.obfuscation_status:
            issues.append("Obfuscation incomplete")
        if not scan.legal_headers:
            issues.append("Missing legal headers")
        if not hardening_report.branch_protection_applied:
            issues.append("Branch protection not configured")
        if not hardening_report.signed_commits_required:
            issues.append("Signed commits not enforced")
        if not (self.repo_root / ".env.secure.template").exists():
            issues.append(".env.secure.template missing")

        remediation: list[str] = []
        if issues:
            remediation.extend(self.auto_fix_issues())

        return SecurityAuditResult(
            scan=scan,
            issues=issues,
            remediation_actions=remediation or hardening_report.actions_taken,
        )

    def auto_fix_issues(self) -> Sequence[str]:
        """Attempt automatic remediation for the most common failures."""

        protection_report = self.code_protector.protect_eliteai_system()
        setup_git_security(self.repo_root)
        template = self.repo_root / ".env.secure.template"
        if not template.exists():
            template.write_text("API_KEYS=ENCRYPTED_BLOB\n", encoding="utf-8")
        return [
            "Applied code protection layers",
            f"Branch protection review: {protection_report.summary()}",
            "Refreshed git security configuration",
            "Verified .env.secure template",
        ]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    audit = CommercialSecurityAudit()
    result = audit.scan_repository()
    print(f"All secure: {result.all_secure}")
    for issue in result.issues:
        print(f" - ISSUE: {issue}")
    for action in result.remediation_actions:
        print(f" - ACTION: {action}")
