"""Streamlit dashboard for interactive fiscal oversight."""

from __future__ import annotations

from typing import Any, Dict

from ..core import ComposableIntelligenceCore
from ..logging import get_logger
from ..datatypes import MonitoringSignal


logger = get_logger(__name__)


def launch_streamlit_dashboard(core: ComposableIntelligenceCore | None = None) -> None:
    """Render a Streamlit dashboard if streamlit is installed."""

    try:  # pragma: no cover - optional dependency
        import streamlit as st
    except Exception as exc:  # pragma: no cover - fallback when streamlit missing
        raise RuntimeError("streamlit is required for the dashboard") from exc

    resolved_core = core or ComposableIntelligenceCore()
    st.set_page_config(page_title="AFOC Command Core", layout="wide")
    st.title("Autonomous Fiscal Command Dashboard")
    st.sidebar.header("Controls")

    overview = resolved_core.healthcheck()
    st.subheader("Platform Health")
    st.json(overview)

    st.subheader("Live Forecast")
    history_text = st.text_input(
        "Historical spend (comma separated)",
        value="1000,1250,1400,1600",
    )
    request_history = [float(value.strip()) for value in history_text.split(",") if value.strip()]
    from ..datatypes import StrategicRoadmap

    roadmap = StrategicRoadmap(
        milestones=["baseline"],
        fiscal_targets={str(index): value for index, value in enumerate(request_history)},
        scenario_assumptions={"seasonality": 1.0},
        growth_projection=1.05,
    )
    forecast = resolved_core.predictive_fiscal_forecasting(roadmap)
    st.metric("Mean forecast", f"${forecast.mean:,.2f}")
    st.line_chart(forecast.ensemble_predictions)

    st.subheader("Operational Spend")
    sample_plan = _sample_plan()
    dashboard = resolved_core.monitor_fiscal_operations(sample_plan)
    st.bar_chart(dashboard.real_time_spending)
    st.json(dashboard.recommended_optimizations)

    monitor = resolved_core.fiscal_monitor
    monitor.initialize([])
    for phase, burn in dashboard.budget_burn_rate.items():
        status = "critical" if burn > 0.45 else "normal"
        monitor.capture_signal(
            MonitoringSignal(signal_name=f"burn::{phase}", value=burn, status=status)
        )
    snapshot = monitor.snapshot()
    breaches = monitor.detect_policy_breaches(snapshot)

    st.subheader("Guardrail Breaches")
    if breaches.breaches:
        st.table(
            {
                breach.policy_name: {
                    "severity": breach.severity,
                    "deviation": breach.deviation,
                    "remediation": ", ".join(breach.remediation_steps),
                }
                for breach in breaches.breaches
            }
        )
    else:
        st.success("No guardrail breaches detected")

    st.subheader("Realtime Event Bus Metrics")
    metrics = resolved_core.get_event_bus_metrics()
    st.json(
        {
            "published": metrics.published,
            "delivered": metrics.delivered,
            "avg_latency": metrics.avg_latency,
            "max_latency": metrics.max_latency,
            "last_event": metrics.last_event_type,
        }
    )

    st.subheader("Reallocation Playground")
    if st.button("Trigger Reinforcement Optimizer"):
        rewards: Dict[str, float] = {
            phase: 1.0 - burn for phase, burn in dashboard.budget_burn_rate.items()
        }
        optimisation = resolved_core.execute_fiscal_optimization_cycle(rewards)
        st.json(optimisation.dict())
    else:
        st.info("Use the button to benchmark the reinforcement allocator against live burn rates.")

    logger.info("Dashboard rendered")


def _sample_plan() -> Any:
    """Build a lightweight strategic plan for dashboard demos."""

    from ..datatypes import StrategicPlan

    return StrategicPlan(
        architecture_budget=120_000.0,
        implementation_budget=240_000.0,
        optimization_budget=80_000.0,
        architectural_tasks=["Refactor core"],
        implementation_tasks=["Deploy integrations"],
        optimization_tasks=["Tune ML lifecycle"],
        technical_constraints=["Budget"],
        fiscal_constraints={"roi_floor": 1.5},
        coding_standards=["PEP8"],
        fiscal_guidelines={"spend_vs_budget": 1.0},
        performance_slas={"latency": 0.2},
        roi_targets={"year1": 1.4},
    )
