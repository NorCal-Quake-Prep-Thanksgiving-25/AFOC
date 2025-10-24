"""Secure deployment entrypoint for the EliteAI Enterprise platform."""
from __future__ import annotations

import logging

from security.auditor import CommercialSecurityAudit
from security.code_protector import CommercialCodeProtector
from security.git_security import secure_git_push, setup_git_security
from security.pre_push_scanner import PrePushSecurityScanner
from security.setup import CommercialRepositorySetup


def deploy_with_security() -> int:
    """One-command secure deployment.

    Returns an exit code so callers can detect failure scenarios.
    """

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("deploy_secure")
    logger.info("🛡️  ACTIVATING COMMERCIAL SECURITY...")

    protector = CommercialCodeProtector()
    report = protector.protect_eliteai_system()
    logger.info("Protection summary: %s", report.summary())

    setup_helper = CommercialRepositorySetup()
    hardening_report = setup_helper.harden_github_repository()
    logger.info("Repository hardening: %s", hardening_report.summary())

    scanner = PrePushSecurityScanner()
    scan_results = scanner.scan_for_vulnerabilities()

    if scan_results.all_secure:
        logger.info("All security checks passed. Configuring git safeguards...")
        setup_git_security()
        audit = CommercialSecurityAudit()
        audit_result = audit.scan_repository()
        if audit_result.all_secure:
            logger.info("Comprehensive audit secure.")
        else:
            logger.warning("Audit issues detected: %s", "; ".join(audit_result.issues))
        secure_git_push()
        logger.info("✅ COMMERCIAL SYSTEM SECURED AND DEPLOYED")
        return 0
    else:
        logger.error("❌ SECURITY ISSUES - DEPLOYMENT BLOCKED")

        issues: list[str] = []
        if scan_results.secrets_detected:
            issues.append(
                "secrets detected: " + ", ".join(sorted(scan_results.secrets_detected))
            )
        if scan_results.ip_exposure:
            issues.append(
                "ip exposure: " + ", ".join(sorted(scan_results.ip_exposure))
            )
        if not scan_results.obfuscation_status:
            issues.append("obfuscation incomplete")
        if not scan_results.legal_headers:
            issues.append("legal headers missing")

        if issues:
            logger.error("Scan issues: %s", "; ".join(issues))

        scanner.auto_fix_issues()
        logger.info("Auto-fix routines executed; manual review still required.")

        return 1


if __name__ == "__main__":
    raise SystemExit(deploy_with_security())

