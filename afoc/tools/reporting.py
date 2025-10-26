"""Utilities for generating artefact reports from orchestrator outputs."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from ..datatypes import FiscalGovernanceFramework, FiscalOperationsDashboard


def export_pdf_summary(
    *,
    governance: FiscalGovernanceFramework,
    dashboard: FiscalOperationsDashboard,
    output_path: str | Path,
) -> Path:
    """Generate a lightweight PDF (or text fallback) summarising insights."""

    destination = Path(output_path)
    try:  # pragma: no cover - optional dependency
        from fpdf import FPDF
    except Exception:
        payload = {
            "governance": asdict(governance),
            "dashboard": asdict(dashboard),
        }
        destination.write_text(json.dumps(payload, indent=2, default=_json_default))
        return destination

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Autonomous Fiscal Orchestration Summary", ln=True)
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 8, f"Total Budget: ${governance.total_budget_allocation:,.2f}", ln=True)
    pdf.multi_cell(
        0, 8, f"Guardrails: {json.dumps(asdict(governance.fiscal_guardrails), indent=2)}"
    )
    pdf.cell(0, 8, "Recommended Optimisations:", ln=True)
    for item in dashboard.recommended_optimizations:
        pdf.multi_cell(0, 6, f"- {item}")
    pdf.add_page()
    pdf.cell(0, 8, "Real-time Spending", ln=True)
    for phase, amount in dashboard.real_time_spending.items():
        pdf.cell(0, 6, f"{phase}: ${amount:,.2f}", ln=True)
    pdf.add_page()
    pdf.cell(0, 8, "Key Performance Indicators", ln=True)
    pdf.cell(
        0,
        6,
        f"Policy violation MTTR: {dashboard.policy_violation_mttr_hours:.1f} hours",
        ln=True,
    )
    for phase, cpu in dashboard.cost_per_unit.items():
        quality = dashboard.quality_scores.get(phase, 0.0)
        pdf.cell(
            0,
            6,
            f"{phase}: cost/unit=${cpu:,.2f}, quality={quality:.2f}",
            ln=True,
        )
    pdf.output(destination)
    return destination


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serialisable")
