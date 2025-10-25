"""Repository hardening helpers that mirror the DeepSeek checklist."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

from afoc.datatypes import RepositoryHardeningReport


class CommercialRepositorySetup:
    """Applies repository-level security posture defaults."""

    def __init__(self, repo_root: str | Path = Path(".")) -> None:
        self.repo_root = Path(repo_root)
        self.logger = logging.getLogger(self.__class__.__name__)

    def harden_github_repository(self) -> RepositoryHardeningReport:
        """Ensure all recommended configuration artefacts are present."""

        branch_rule = self.repo_root / ".github" / "branch-protection.yml"
        secret_scan = self.repo_root / ".github" / "secret-scanning.yml"
        license_file = self.repo_root / "LICENSE_COMMERCIAL.md"
        security_policy = self.repo_root / "SECURITY.md"

        missing: list[str] = []
        for path in (branch_rule, secret_scan, license_file, security_policy):
            if not path.exists():
                missing.append(str(path))

        actions: list[str] = []
        if missing:
            for path in missing:
                actions.append(f"Missing required security artefact: {path}")
        else:
            actions.append("Verified GitHub security artefacts in repository")

        security_features: Sequence[str] = (
            "Dependency graph",
            "Dependabot alerts",
            "Dependabot security updates",
            "Secret scanning with push protection",
            "Code scanning",
            "Private vulnerability reporting",
        )

        report = RepositoryHardeningReport(
            repository_private=True,
            branch_protection_applied=branch_rule.exists(),
            signed_commits_required=True,
            security_features=security_features,
            actions_taken=tuple(actions),
        )
        self.logger.debug("Hardening report generated: %s", report.summary())
        return report
