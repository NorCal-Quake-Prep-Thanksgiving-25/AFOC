"""Command-line entry point for the pre-push security checklist."""
from __future__ import annotations

import argparse
import logging

from .auditor import CommercialSecurityAudit
from .pre_push_scanner import PrePushSecurityScanner


LOGGER = logging.getLogger("security.scanner")


def run(args: argparse.Namespace) -> int:
    scanner = PrePushSecurityScanner()
    result = scanner.scan_for_vulnerabilities()

    LOGGER.info("All secure: %s", result.all_secure)
    if args.check_secrets and result.secrets_detected:
        LOGGER.error("Secrets detected: %s", ", ".join(result.secrets_detected))
    if args.check_ips and result.ip_exposure:
        LOGGER.error("IP exposure detected: %s", ", ".join(result.ip_exposure))
    if args.obfuscate and not result.obfuscation_status:
        LOGGER.info("Triggering automatic obfuscation pass...")
        scanner.auto_fix_issues()

    if args.full_audit:
        audit = CommercialSecurityAudit()
        audit_result = audit.scan_repository()
        LOGGER.info("Audit secure: %s", audit_result.all_secure)
        for issue in audit_result.issues:
            LOGGER.error("AUDIT ISSUE: %s", issue)
        for action in audit_result.remediation_actions:
            LOGGER.info("AUDIT ACTION: %s", action)
        return 0 if audit_result.all_secure else 1

    return 0 if result.all_secure else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="EliteAI security scanner")
    parser.add_argument("--check-secrets", action="store_true", help="Fail if secrets are detected")
    parser.add_argument("--check-ips", action="store_true", help="Fail if IP leakage is detected")
    parser.add_argument("--obfuscate", action="store_true", help="Autofix by obfuscating code on failure")
    parser.add_argument("--full-audit", action="store_true", help="Run the comprehensive security audit")
    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = build_parser()
    args = parser.parse_args()
    exit_code = run(args)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
