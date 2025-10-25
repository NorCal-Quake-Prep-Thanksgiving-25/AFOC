"""High-level orchestration for commercial code protection."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

from afoc.datatypes import ProtectionReport

from .commercial_ip_guard import CommercialIPGuard
from .legal_guard import LegalProtectionAutomation
from .obfuscation import CodeProtector


class CommercialCodeProtector:
    """Protects core IP from theft and reverse engineering."""

    def __init__(self, repo_root: str | Path = Path(".")) -> None:
        self.repo_root = Path(repo_root)
        self.valuation = "$25,000,000"
        self.protection_layers = (
            "algorithm_obfuscation",
            "sensitive_code_encryption",
            "runtime_decryption",
            "digital_watermarking",
            "legal_automation",
        )
        self.logger = logging.getLogger(self.__class__.__name__)
        self.obfuscation_engine = CodeProtector(self.repo_root)
        self.legal_automation = LegalProtectionAutomation()
        self.ip_guard = CommercialIPGuard(self.repo_root)

    def protect_eliteai_system(self, modules: Sequence[str] | None = None) -> ProtectionReport:
        modules = modules or (
            "quantum_roi_engine",
            "fiscal_cognition",
            "autonomous_business_development",
            "industry_intelligence",
            "core",
        )
        self.logger.info("Applying protection layers to modules: %s", modules)

        obfuscated_modules = []
        protected_payloads = self.obfuscation_engine.protect_sensitive_code(modules)
        for module, payload in protected_payloads.items():
            obfuscated_modules.append(f"{module}:{len(payload)}")

        legal_headers = self.legal_automation.generate_headers(modules)
        watermarks = self.ip_guard.watermark_outputs(modules)

        report = ProtectionReport(
            obfuscated_modules=obfuscated_modules,
            encrypted_business_logic="AES-256 + RSA-4096",
            legal_headers=legal_headers,
            watermarking=", ".join(f"{k}:{v}" for k, v in watermarks.items()),
        )
        self.logger.info("Protection report generated: %s", report.summary())
        return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    protector = CommercialCodeProtector()
    protection_report = protector.protect_eliteai_system()
    print(protection_report.summary())

