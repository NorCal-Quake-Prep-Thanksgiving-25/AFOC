from __future__ import annotations

import asyncio
import json

from afoc.agents.event_bus import AgentEvent
from afoc.datatypes import (
    FiscalGovernanceFramework,
    FiscalGuardrails,
    FiscalOperationsDashboard,
)
from afoc.integrations.alerts import AlertDispatcher, AlertResult
from afoc.tools.reporting import export_pdf_summary


class _DummyNotifier:
    def __init__(self, channel: str) -> None:
        self.channel = channel
        self.messages: list[str] = []

    def notify(self, *args, **kwargs) -> AlertResult:  # type: ignore[override]
        if self.channel == "email":
            subject, body = args
            self.messages.append(f"{subject}:{body}")
        else:
            (message,) = args
            self.messages.append(message)
        return AlertResult(True, self.channel, "delivered")


def test_alert_dispatcher_triggers_channels() -> None:
    slack = _DummyNotifier("slack")
    email = _DummyNotifier("email")
    dispatcher = AlertDispatcher(slack_notifier=slack, email_notifier=email)

    event = AgentEvent(
        type="forecast.completed",
        payload={"anomalies": [0, 1, 2], "diagnostics": {"ensemble_divergence": 0.4}},
    )
    asyncio.run(dispatcher.handle_event(event))

    assert slack.messages
    assert email.messages

    security_event = AgentEvent(
        type="security.alert", payload={"severity": "high", "message": "breach"}
    )
    asyncio.run(dispatcher.handle_event(security_event))

    assert any("breach" in message for message in slack.messages)


def test_export_pdf_summary_fallback(tmp_path) -> None:
    framework = FiscalGovernanceFramework(
        total_budget_allocation=1000.0,
        budget_distribution={"architecture": 500.0, "ops": 500.0},
        fiscal_guardrails=FiscalGuardrails(
            maximum_allocation=600.0,
            minimum_quality_threshold=0.8,
            risk_tolerance=0.4,
            escalation_threshold=0.2,
        ),
        cost_quality_ratios={"architecture": 0.5, "ops": 0.5},
        resource_efficiency_targets={"architecture": 1.2, "ops": 1.1},
        roi_thresholds={"architecture": 1.2, "ops": 1.1},
        spending_velocity_controls={"architecture": 0.1, "ops": 0.2},
        auto_reallocation_triggers={"architecture": 0.2, "ops": 0.2},
        fiscal_health_monitors={"architecture": 0.95, "ops": 0.9},
    )
    dashboard = FiscalOperationsDashboard(
        real_time_spending={"architecture": 500.0, "ops": 500.0},
        cost_performance_metrics={"architecture": 0.5, "ops": 0.5},
        budget_burn_rate={"architecture": 0.6, "ops": 0.4},
        fiscal_health_score=0.8,
        recommended_optimizations=["Shift budget to architecture"],
        resource_reallocation_directives={"architecture": 0.1},
        cost_quality_adjustments={},
    )
    output = export_pdf_summary(
        governance=framework,
        dashboard=dashboard,
        output_path=tmp_path / "report.pdf",
    )
    content = json.loads(output.read_text())
    assert content["governance"]["total_budget_allocation"] == 1000.0
