"""Composable intelligence core orchestrating fiscal optimization."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Mapping, Sequence

from .agents import (
    AllocationRequest,
    AllocationResponse,
    AsyncEventBus,
    EventBusMetrics,
    BudgetAgent,
    ForecastAgent,
    ForecastRequest,
    ForecastResponse,
    ROIEngine,
    OptimizationRequest,
    OptimizationResponse,
    SecurityGuardian,
)
from .credentials import CredentialProvider, default_credential_provider
from .data import DataFabric, DataFabricConfig, IngestionReport
from .datatypes import (
    FiscalGovernanceFramework,
    FiscalGuardrails,
    FiscalOperationsDashboard,
    OversightRecord,
    OversightSummary,
    StrategicAnalysis,
    StrategicPlan,
    StrategicRoadmap,
)
from .integrations import (
    AVAILABLE_COLLECTORS,
    AVAILABLE_DEVOPS_COLLECTORS,
    AVAILABLE_USAGE_COLLECTORS,
)
from .logging import get_logger
from .monitoring import AFOCPerformanceMonitor, FiscalMonitor
from .plugins import registry as plugin_registry


class ComposableIntelligenceCore:
    """Event-driven mesh of agents powering fiscal orchestration."""

    def __init__(
        self,
        *,
        data_fabric: DataFabric | None = None,
        event_bus: AsyncEventBus | None = None,
        credential_provider: CredentialProvider | None = None,
    ) -> None:
        self.logger = get_logger(__name__)
        self.event_bus = event_bus or AsyncEventBus()
        self.credential_provider = credential_provider or default_credential_provider
        self.data_fabric = data_fabric or DataFabric(
            DataFabricConfig(), credential_provider=self.credential_provider
        )
        self.performance = AFOCPerformanceMonitor()
        self.fiscal_monitor = FiscalMonitor()
        self._fiscal_records: list[OversightRecord] = []

        self.budget_agent = BudgetAgent(self.event_bus)
        self.forecast_agent = ForecastAgent(self.event_bus)
        self.roi_engine = ROIEngine(self.event_bus)
        self.security_guardian = SecurityGuardian(self.event_bus)

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._register_default_plugins()
        self.logger.debug("Composable core initialised", health=self.healthcheck())

    # ------------------------------------------------------------------
    # Agent request helpers
    # ------------------------------------------------------------------
    def budget_agent_request_model(self, **kwargs: Any) -> AllocationRequest:
        return AllocationRequest(**kwargs)

    def forecast_agent_request_model(self, **kwargs: Any) -> ForecastRequest:
        return ForecastRequest(**kwargs)

    def optimization_request_model(self, **kwargs: Any) -> OptimizationRequest:
        return OptimizationRequest(**kwargs)

    # ------------------------------------------------------------------
    # Plugin lifecycle
    # ------------------------------------------------------------------
    def _register_default_plugins(self) -> None:
        for name, cost_collector in AVAILABLE_COLLECTORS.items():
            plugin_registry.unregister(name)
            plugin_registry.register(name, cost_collector)
        for name, usage_collector in AVAILABLE_USAGE_COLLECTORS.items():
            plugin_registry.unregister(name)
            plugin_registry.register(name, usage_collector)
        for name, devops_collector in AVAILABLE_DEVOPS_COLLECTORS.items():
            plugin_registry.unregister(name)
            plugin_registry.register(name, devops_collector)

    def register_plugin(self, name: str, factory: Any) -> None:
        plugin_registry.unregister(name)
        plugin_registry.register(name, factory)

    # ------------------------------------------------------------------
    # Governance orchestrations
    # ------------------------------------------------------------------
    def establish_fiscal_governance(
        self, strategic_analysis: StrategicAnalysis
    ) -> FiscalGovernanceFramework:
        request = self.budget_agent_request_model(
            total_budget=max(1.0, strategic_analysis.feasibility_score * 100.0),
            targets=dict(strategic_analysis.alignment_vector),
        )
        response = self._run_async(self.budget_agent.allocate(request))
        guardrails = FiscalGuardrails(
            maximum_allocation=max(response.allocations.values(), default=0.0),
            minimum_quality_threshold=0.8,
            risk_tolerance=0.4,
            escalation_threshold=0.2,
        )
        framework = FiscalGovernanceFramework(
            total_budget_allocation=request.total_budget,
            budget_distribution=response.allocations,
            fiscal_guardrails=guardrails,
            cost_quality_ratios={
                k: v / request.total_budget for k, v in response.allocations.items()
            },
            resource_efficiency_targets={k: response.efficiency_gain for k in response.allocations},
            roi_thresholds={k: 1.2 for k in response.allocations},
            spending_velocity_controls={k: 0.1 for k in response.allocations},
            auto_reallocation_triggers={k: 0.15 for k in response.allocations},
            fiscal_health_monitors={k: 0.95 for k in response.allocations},
        )
        self.data_fabric.ingest_records(
            (
                {
                    "id": f"governance-{phase}",
                    "workload": phase,
                    "amount": allocation,
                    "source": "governance",
                }
                for phase, allocation in response.allocations.items()
            ),
            source="governance",
        )
        self.logger.info("Governance established", allocations=response.allocations)
        return framework

    def predictive_fiscal_forecasting(
        self, strategic_roadmap: StrategicRoadmap
    ) -> ForecastResponse:
        history = [float(value) for value in strategic_roadmap.fiscal_targets.values()]
        request = self.forecast_agent_request_model(historical_spend=history)
        forecast = self._run_async(self.forecast_agent.forecast(request))
        self.logger.info(
            "Forecast completed",
            mean=forecast.mean,
            upper=forecast.upper,
            lower=forecast.lower,
            history_len=len(history),
        )
        return forecast

    def execute_fiscal_optimization_cycle(
        self, rewards: Mapping[str, float]
    ) -> OptimizationResponse:
        request = self.optimization_request_model(
            reward_history=list(rewards.values()),
            actions=list(rewards.keys()),
        )
        return self._run_async(self.roi_engine.optimize(request))

    def monitor_fiscal_operations(self, plan: StrategicPlan) -> FiscalOperationsDashboard:
        spend = {
            "architecture": plan.architecture_budget,
            "implementation": plan.implementation_budget,
            "optimization": plan.optimization_budget,
        }
        denominator = max(sum(spend.values()), 1.0)
        burn = {phase: amount / denominator for phase, amount in spend.items()}
        health_score = sum(burn.values()) / max(len(burn), 1)
        self._fiscal_records.clear()
        dashboard = FiscalOperationsDashboard(
            real_time_spending=spend,
            cost_performance_metrics={phase: value for phase, value in burn.items()},
            budget_burn_rate=burn,
            fiscal_health_score=1.0 - health_score,
            recommended_optimizations=[
                f"Increase efficiency for {phase}" for phase, value in burn.items() if value > 0.4
            ],
            resource_reallocation_directives={},
            cost_quality_adjustments={},
        )
        self.data_fabric.ingest_records(
            (
                {
                    "id": f"ops-{phase}",
                    "workload": phase,
                    "amount": amount,
                    "source": "operations",
                }
                for phase, amount in spend.items()
            ),
            source="operations",
        )
        return dashboard

    def validate_strategic_fiscal_alignment(
        self, dashboard: FiscalOperationsDashboard
    ) -> OversightSummary:
        record = OversightRecord(
            phase="composite",
            approved=dashboard.fiscal_health_score >= 0.5,
            strategic_score=dashboard.fiscal_health_score,
            fiscal_score=dashboard.fiscal_health_score,
            budget_consumed=sum(dashboard.real_time_spending.values()),
            commentary="Automated validation via composable agents",
        )
        return OversightSummary(
            records=[record],
            strategic_average=dashboard.fiscal_health_score,
            fiscal_average=dashboard.fiscal_health_score,
            total_budget_consumed=sum(dashboard.real_time_spending.values()),
        )

    # ------------------------------------------------------------------
    # Data fabric integrations
    # ------------------------------------------------------------------
    def ingest_collector_payload(
        self, records: Sequence[Mapping[str, Any]], *, source: str
    ) -> IngestionReport:
        normalised = [dict(record) for record in records]
        report = self.data_fabric.ingest_records(normalised, source=source)
        self.logger.info(
            "Ingestion completed",
            source=source,
            ingested=report.ingested,
            cached=report.cached,
            failures=len(report.failed),
        )
        return report

    def healthcheck(self) -> Dict[str, Any]:
        metrics = self.event_bus.metrics()
        fabric_status = self.data_fabric.healthcheck()
        return {
            "event_bus": {
                "published": metrics.published,
                "delivered": metrics.delivered,
                "avg_latency": metrics.avg_latency,
                "max_latency": metrics.max_latency,
            },
            "data_fabric": fabric_status,
        }

    # ------------------------------------------------------------------
    # Oversight utilities
    # ------------------------------------------------------------------
    def evaluate_phase(
        self,
        phase_name: str,
        strategic_score: float,
        fiscal_score: float,
        budget_allocation: float,
    ) -> OversightRecord:
        record = OversightRecord(
            phase=phase_name,
            approved=strategic_score >= 0.5 and fiscal_score >= 0.5,
            strategic_score=strategic_score,
            fiscal_score=fiscal_score,
            budget_consumed=budget_allocation,
            commentary="Evaluated via composable intelligence core",
        )
        self._fiscal_records.append(record)
        return record

    def get_fiscal_report(self) -> Mapping[str, float]:
        summary = self.fiscal_monitor.summarize_oversight(self._fiscal_records)
        return {
            "strategic_average": summary.strategic_average,
            "fiscal_average": summary.fiscal_average,
            "total_budget_consumed": summary.total_budget_consumed,
        }

    def get_event_bus_metrics(self) -> EventBusMetrics:
        """Expose event bus metrics for observability surfaces."""

        return self.event_bus.metrics()

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def _run_async(self, awaitable: Any) -> Any:
        return self._loop.run_until_complete(awaitable)


class AutonomousFiscalOrchestrationCore(ComposableIntelligenceCore):
    """Backwards compatible alias for callers expecting the legacy class."""

    pass
