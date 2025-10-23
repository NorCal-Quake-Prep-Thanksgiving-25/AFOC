"""Self-writing documentation utilities for EliteAI."""
from __future__ import annotations

from typing import Mapping, Sequence

from .datatypes import DocumentationSuite, PersonalizedPitchDeck


class SelfWritingDocumentation:
    """Generates commercial collateral programmatically."""

    def generate_commercial_package(self) -> DocumentationSuite:
        whitepaper = self._build_whitepaper()
        return DocumentationSuite(
            technical_white_paper=whitepaper,
            business_value_proposition="Dynamic ROI calculator embedded in analytics portal",
            competitive_analysis="Live benchmarking across top 10 competitors",
            case_study_library=self._case_studies(),
            implementation_guides=self._implementation_guides(),
            security_compliance=self._compliance_assets(),
        )

    def create_adaptive_pitch_decks(self, prospect_profile: Mapping[str, str]) -> PersonalizedPitchDeck:
        persona = prospect_profile.get("role", "executive")
        market = prospect_profile.get("industry", "enterprise")
        executive_summary = f"EliteAI unlocks hypergrowth for {market} leaders"
        technical_details = f"Architecture tuned for {market} regulatory requirements"
        financial_analysis = (
            f"Projected ROI aligns with {persona.upper()} priorities and accelerates strategic outcomes"
        )
        implementation_timeline = "Phase-gated rollout completed within 45-60 days"

        return PersonalizedPitchDeck(
            executive_summary=executive_summary,
            technical_details=technical_details,
            financial_analysis=financial_analysis,
            implementation_timeline=implementation_timeline,
        )

    @staticmethod
    def _build_whitepaper() -> str:
        sections = [
            "Executive Overview",
            "Technical Architecture",
            "Security Model",
            "Performance Benchmarks",
            "Implementation Roadmap",
        ]
        body = [f"# {title}\nEliteAI provides detailed insights for {title.lower()}." for title in sections]
        return "\n\n".join(body)

    @staticmethod
    def _case_studies() -> Sequence[str]:
        return [
            "Finance: $80M savings through predictive budgeting",
            "Healthcare: Reduced patient wait times by 45%",
            "Energy: Increased grid efficiency by 18%",
        ]

    @staticmethod
    def _implementation_guides() -> Sequence[str]:
        return [
            "30-day onboarding blueprint",
            "Integration checklist for enterprise systems",
            "Security hardening guide",
        ]

    @staticmethod
    def _compliance_assets() -> Sequence[str]:
        return [
            "SOC2 Type II controls",
            "HIPAA readiness toolkit",
            "GDPR cross-border checklist",
        ]

