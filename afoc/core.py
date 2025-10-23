"""Autonomous Fiscal Orchestration Core implementation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Mapping, Optional, Sequence

from .budget_core import BudgetCore
from .cost_quality import CostQualityEngine, CostQualityMetric
from .datatypes import (
    EquilibriumPoint,
    FiscalForecast,
    FiscalGovernanceFramework,
    FiscalGuardrails,
    FiscalOperationsDashboard,
    FiscalOptimizationReport,
    IntegrationAdapter,
    IntegrationAdapterReport,
    IntegrationSummary,
    LedgerEntry,
    LedgerHealth,
    MonitoringSignal,
    OptimizationRecord,
    OversightInterface,
    OversightRecord,
    OversightSummary,
    PolicyAdjustment,
    ReallocationReport,
    ResourceRecommendationSet,
    ResourceTelemetryBatch,
    StrategicAnalysis,
    StrategicPlan,
    StrategicRoadmap,
    ViabilityReport,
)
from .fiscal_cognition import FiscalCognitionUnit
from .ledger import DistributedFiscalLedger
from .monitoring import AFOCPerformanceMonitor, FiscalMonitor
from .resource_conductor import ResourceConductor, ResourceSnapshot
from .roi import ValueReturnCalculator


@dataclass
class RealTimeSpendingTracker:
    ledger: DistributedFiscalLedger

    def track(self, plan: StrategicPlan) -> Mapping[str, float]:
        snapshot = self.ledger.snapshot("enterprise")
        if snapshot.totals:
            return snapshot.totals
        return {
            "architecture": plan.architecture_budget,
            "implementation": plan.implementation_budget,
            "optimization": plan.optimization_budget,
        }


class EquilibriumOptimizer:
    def __init__(self, engine: CostQualityEngine) -> None:
        self.engine = engine

    def optimize(self, metrics: Sequence[CostQualityMetric]) -> FiscalOptimizationReport:
        report = FiscalOptimizationReport()
        state = self.engine.maintain_equilibrium(metrics)
        metric_map = {metric.component: metric for metric in metrics}
        for directive in state.adjustment_actions:
            component, action = directive.split(":")
            metric = metric_map.get(component)
            if not metric:
                continue
            optimal = state.optimal_targets.get(component, metric.efficiency())
            efficiency_gain = state.efficiency_gains.get(component, 0.0)
            equilibrium = EquilibriumPoint(
                optimal_cost=metric.cost * 0.95,
                optimal_quality=metric.quality * 1.05,
                efficiency_score=optimal + efficiency_gain,
                explanation=f"Action {action} recommended",
            )
            report.add_optimization(
                OptimizationRecord(
                    component_name=component,
                    previous_cost=metric.cost,
                    previous_value=metric.quality,
                    new_cost=equilibrium.optimal_cost,
                    new_value=equilibrium.optimal_quality,
                    equilibrium=equilibrium,
                    reasoning=f"Directive {action} applied",
                )
            )
        return report


class AutonomousFiscalOrchestrationCore:
    """Central nervous system orchestrating fiscal operations."""

    def __init__(self) -> None:
        self.fiscal_cognition = FiscalCognitionUnit()
        self.cost_quality_engine = CostQualityEngine()
        self.resource_orchestrator = ResourceConductor()
        self.budget_intelligence = BudgetCore()
        self.fiscal_ledger = DistributedFiscalLedger()
        self.fiscal_monitor = FiscalMonitor()
        self.value_return = ValueReturnCalculator()
        self.real_time_tracker = RealTimeSpendingTracker(self.fiscal_ledger)
        self.performance_monitor = AFOCPerformanceMonitor()
        self._governance_cache: dict[str, FiscalGovernanceFramework] = {}
        self._allocation_cache: dict[str, Mapping[str, float]] = {}
        self._equilibrium_cache: dict[tuple[float, float], EquilibriumPoint] = {}
        self._optimization_cache: dict[str, FiscalOptimizationReport] = {}
        self._lazy_results: dict[str, FiscalOptimizationReport] = {}
        self._precomputed_allocations = self._precompute_common_allocations()
        self._oversight_records: list[OversightRecord] = []
        self._latest_dashboard: Optional[FiscalOperationsDashboard] = None

    # Performance helpers --------------------------------------------------
    def _mapping_signature(self, mapping: Mapping[str, float]) -> tuple[tuple[str, float], ...]:
        return tuple(sorted((key, round(value, 4)) for key, value in mapping.items()))

    def _strategic_signature(self, strategic_analysis: StrategicAnalysis) -> str:
        alignment = self._mapping_signature(strategic_analysis.alignment_vector)
        narrative_hash = hash(strategic_analysis.narrative)
        return f"{strategic_analysis.feasibility_score:.4f}|{alignment}|{narrative_hash}"

    def _components_signature(self, system_components: Sequence[Mapping[str, float]]) -> str:
        normalized = tuple(self._mapping_signature(component) for component in system_components)
        return str(normalized)

    def _allocation_key(self, budget: float, quality_target: float) -> str:
        return f"{round(budget, 2):.2f}:{round(quality_target, 2):.2f}"

    def _precompute_common_allocations(self) -> dict[str, Mapping[str, float]]:
        patterns: dict[str, Mapping[str, float]] = {}
        budgets = [1000, 5000, 10000, 50000, 100000]
        quality_targets = [0.7, 0.8, 0.9, 0.95]
        for budget in budgets:
            for quality in quality_targets:
                base = {
                    "architecture": budget * 0.35 * quality,
                    "implementation": budget * 0.45 * quality,
                    "optimization": budget * 0.2 * quality,
                }
                key = self._allocation_key(budget, quality)
                allocation = self.resource_orchestrator.calculate_optimal_allocation(base)
                patterns[key] = allocation
        return patterns

    def get_precomputed_allocation(self, budget: float, quality_target: float) -> Mapping[str, float]:
        key = self._allocation_key(budget, quality_target)
        cached = self._precomputed_allocations.get(key)
        if cached is not None:
            self.performance_monitor.record_cache_event("precomputed_allocation", True)
            return cached
        self.performance_monitor.record_cache_event("precomputed_allocation", False)
        base = {
            "architecture": budget * 0.35 * quality_target,
            "implementation": budget * 0.45 * quality_target,
            "optimization": budget * 0.2 * quality_target,
        }
        allocation = self.resource_orchestrator.calculate_optimal_allocation(base)
        if len(self._precomputed_allocations) < 200:
            self._precomputed_allocations[key] = allocation
        return allocation

    def get_lazy_optimization(
        self, system_components: Sequence[Mapping[str, float]], force_recompute: bool = False
    ) -> FiscalOptimizationReport:
        signature = self._components_signature(system_components)
        cached = self._lazy_results.get(signature)
        if cached is not None and not force_recompute:
            self.performance_monitor.record_cache_event("lazy_optimization", True)
            return cached
        self.performance_monitor.record_cache_event("lazy_optimization", False)
        if force_recompute:
            self.performance_monitor.record_cache_event("optimization_cycle", False)
            report = self.performance_monitor.time_call(
                "optimization_cycle", lambda: self._run_optimization_cycle(system_components)
            )
        else:
            report = self.execute_fiscal_optimization_cycle(system_components)
        self._lazy_results[signature] = report
        self._optimization_cache[signature] = report
        return report

    # Governance -----------------------------------------------------------
    def establish_fiscal_governance(self, strategic_analysis: StrategicAnalysis) -> FiscalGovernanceFramework:
        signature = self._strategic_signature(strategic_analysis)
        cached = self._governance_cache.get(signature)
        if cached is not None:
            self.performance_monitor.record_cache_event("fiscal_governance", True)
            return cached

        self.performance_monitor.record_cache_event("fiscal_governance", False)

        def compute() -> FiscalGovernanceFramework:
            normalized_alignment = self._normalize_alignment(strategic_analysis.alignment_vector)
            base_budget = max(100.0, strategic_analysis.feasibility_score * 25)
            budget_distribution = {
                phase: base_budget * weight
                for phase, weight in normalized_alignment.items()
            }
            guardrails = self.establish_fiscal_guardrails(strategic_analysis, normalized_alignment)
            ratios = self.calculate_optimal_cost_quality_ratios(strategic_analysis, normalized_alignment)
            efficiency = self.set_efficiency_targets(strategic_analysis, normalized_alignment)
            roi_thresholds = self.establish_roi_requirements(strategic_analysis, normalized_alignment)
            velocity = self.implement_velocity_controls()
            reallocation = self.set_reallocation_triggers()
            monitors = self.deploy_fiscal_monitors()
            framework = FiscalGovernanceFramework(
                total_budget_allocation=sum(budget_distribution.values()),
                budget_distribution=budget_distribution,
                fiscal_guardrails=guardrails,
                cost_quality_ratios=ratios,
                resource_efficiency_targets=efficiency,
                roi_thresholds=roi_thresholds,
                spending_velocity_controls=velocity,
                auto_reallocation_triggers=reallocation,
                fiscal_health_monitors=monitors,
            )
            self._allocation_cache[signature] = budget_distribution
            return framework

        framework = self.performance_monitor.time_call("fiscal_governance_setup", compute)
        self._governance_cache[signature] = framework
        return framework

    def _normalize_alignment(self, alignment_vector: Mapping[str, float]) -> Mapping[str, float]:
        total = sum(alignment_vector.values()) or 1.0
        return {phase: value / total for phase, value in alignment_vector.items()}

    def establish_fiscal_guardrails(
        self,
        strategic_analysis: StrategicAnalysis,
        normalized_alignment: Optional[Mapping[str, float]] = None,
    ) -> FiscalGuardrails:
        normalized_alignment = normalized_alignment or self._normalize_alignment(
            strategic_analysis.alignment_vector
        )
        highest_phase = max(normalized_alignment, key=normalized_alignment.get)
        return FiscalGuardrails(
            maximum_allocation=strategic_analysis.feasibility_score * 35,
            minimum_quality_threshold=0.9,
            risk_tolerance=max(0.4, normalized_alignment[highest_phase]),
            escalation_threshold=0.85,
            notes=strategic_analysis.narrative,
        )

    def calculate_optimal_cost_quality_ratios(
        self,
        strategic_analysis: StrategicAnalysis,
        normalized_alignment: Optional[Mapping[str, float]] = None,
    ) -> Mapping[str, float]:
        normalized_alignment = normalized_alignment or self._normalize_alignment(
            strategic_analysis.alignment_vector
        )
        return {phase: round(weight * 1.5, 3) for phase, weight in normalized_alignment.items()}

    def set_efficiency_targets(
        self,
        strategic_analysis: StrategicAnalysis,
        normalized_alignment: Optional[Mapping[str, float]] = None,
    ) -> Mapping[str, float]:
        normalized_alignment = normalized_alignment or self._normalize_alignment(
            strategic_analysis.alignment_vector
        )
        baseline = max(0.75, strategic_analysis.feasibility_score / 120)
        return {
            phase: min(0.95, baseline + weight * 0.2)
            for phase, weight in normalized_alignment.items()
        }

    def establish_roi_requirements(
        self,
        strategic_analysis: StrategicAnalysis,
        normalized_alignment: Optional[Mapping[str, float]] = None,
    ) -> Mapping[str, float]:
        normalized_alignment = normalized_alignment or self._normalize_alignment(
            strategic_analysis.alignment_vector
        )
        base_roi = max(0.1, strategic_analysis.feasibility_score / 150)
        return {phase: base_roi + weight * 0.35 for phase, weight in normalized_alignment.items()}

    def implement_velocity_controls(self) -> Mapping[str, float]:
        return {"architecture": 1.2, "implementation": 1.0, "optimization": 0.8}

    def set_reallocation_triggers(self) -> Mapping[str, float]:
        return {"architecture": 0.1, "implementation": 0.15, "optimization": 0.2}

    def deploy_fiscal_monitors(self) -> Mapping[str, float]:
        return {"spending_velocity": 0.95, "roi": 0.9}

    # Monitoring -----------------------------------------------------------
    def initialize_fiscal_monitoring(self, strategic_plan: StrategicPlan) -> FiscalMonitor:
        policies = [
            PolicyAdjustment(
                policy_name=phase,
                adjustment_value=value,
                justification="Initial fiscal constraint",
                effective_date=datetime.utcnow(),
            )
            for phase, value in strategic_plan.fiscal_constraints.items()
        ]
        self.fiscal_monitor.initialize(policies)
        self._oversight_records.clear()
        return self.fiscal_monitor

    def track_resource_consumption(self, execution_workflow: Mapping[str, float]) -> Mapping[str, float]:
        return dict(execution_workflow)

    def calculate_cost_efficiency(
        self,
        execution_workflow: Mapping[str, float],
        fiscal_guidelines: Optional[Mapping[str, float]] = None,
    ) -> Mapping[str, float]:
        fiscal_guidelines = fiscal_guidelines or {}
        efficiency: dict[str, float] = {}
        for phase, spend in execution_workflow.items():
            guideline = fiscal_guidelines.get(phase) or spend or 1.0
            efficiency[phase] = min(1.5, spend / guideline)
        return efficiency

    def calculate_burn_rate(
        self,
        execution_workflow: Mapping[str, float],
        total_budget: Optional[float] = None,
    ) -> Mapping[str, float]:
        total = total_budget or sum(execution_workflow.values()) or 1.0
        return {phase: value / total for phase, value in execution_workflow.items()}

    def compute_fiscal_health(self, execution_workflow: Mapping[str, float]) -> float:
        burn = self.calculate_burn_rate(execution_workflow)
        largest = max(burn.values()) if burn else 0.0
        return round(max(0.0, 1.0 - largest), 3)

    def identify_cost_savings(self, execution_workflow: Mapping[str, float]) -> Sequence[str]:
        return [f"Renegotiate contract spend in {phase}" for phase in execution_workflow]

    def calculate_optimal_reallocation(self, execution_workflow: Mapping[str, float]) -> Mapping[str, float]:
        total = sum(execution_workflow.values()) or 1.0
        return {phase: value / total * 0.1 for phase, value in execution_workflow.items()}

    def adjust_quality_levels(self, execution_workflow: Mapping[str, float]) -> Mapping[str, float]:
        return {phase: round(1.0 - (idx * 0.02), 3) for idx, phase in enumerate(execution_workflow)}

    def deploy_fiscal_monitors_dashboard(
        self,
        execution_workflow: Mapping[str, float],
        fiscal_guidelines: Optional[Mapping[str, float]] = None,
        total_budget: Optional[float] = None,
    ) -> FiscalOperationsDashboard:
        spending = self.track_resource_consumption(execution_workflow)
        cost_efficiency = self.calculate_cost_efficiency(execution_workflow, fiscal_guidelines)
        burn_rate = self.calculate_burn_rate(execution_workflow, total_budget)
        health = self.compute_fiscal_health(execution_workflow)
        optimizations = self.identify_cost_savings(execution_workflow)
        reallocations = self.calculate_optimal_reallocation(execution_workflow)
        quality = self.adjust_quality_levels(execution_workflow)
        return FiscalOperationsDashboard(
            real_time_spending=spending,
            cost_performance_metrics=cost_efficiency,
            budget_burn_rate=burn_rate,
            fiscal_health_score=health,
            recommended_optimizations=optimizations,
            resource_reallocation_directives=reallocations,
            cost_quality_adjustments=quality,
        )

    def monitor_fiscal_operations(
        self,
        execution_workflow: Mapping[str, float],
        fiscal_guidelines: Optional[Mapping[str, float]] = None,
        total_budget: Optional[float] = None,
    ) -> FiscalOperationsDashboard:
        dashboard = self.deploy_fiscal_monitors_dashboard(
            execution_workflow,
            fiscal_guidelines=fiscal_guidelines,
            total_budget=total_budget,
        )
        for phase, value in execution_workflow.items():
            status = "critical" if dashboard.cost_performance_metrics.get(phase, 0) > 1.2 else "normal"
            self.fiscal_monitor.capture_signal(
                MonitoringSignal(signal_name=f"spend:{phase}", value=value, status=status)
            )
        self._latest_dashboard = dashboard
        return dashboard

    # Optimization ---------------------------------------------------------
    def measure_component_cost(self, component: Mapping[str, float]) -> float:
        return sum(component.values())

    def measure_component_value(self, component: Mapping[str, float]) -> float:
        return sum(value * 1.1 for value in component.values())

    def calculate_cost_quality_equilibrium(self, current_cost: float, current_value: float) -> EquilibriumPoint:
        key = (round(current_cost, 2), round(current_value, 2))
        cached = self._equilibrium_cache.get(key)
        if cached is not None:
            self.performance_monitor.record_cache_event("equilibrium_analysis", True)
            return cached

        self.performance_monitor.record_cache_event("equilibrium_analysis", False)

        def compute() -> EquilibriumPoint:
            metric = CostQualityMetric(
                component="ad_hoc",
                cost=current_cost,
                quality=current_value,
                benchmark_cost=current_cost * 0.95,
                benchmark_quality=current_value * 0.98,
            )
            envelope = self.cost_quality_engine.calculate_equilibrium_frontier([metric])
            directives = envelope.directives
            optimal = directives.optimal_points.get("ad_hoc", metric.efficiency())
            gain = directives.expected_improvements.get("ad_hoc", 0.0)
            return EquilibriumPoint(
                optimal_cost=metric.benchmark_cost,
                optimal_quality=metric.benchmark_quality,
                efficiency_score=optimal + gain,
                explanation="Derived from equilibrium frontier analysis",
            )

        equilibrium = self.performance_monitor.time_call("equilibrium_analysis", compute)
        self._equilibrium_cache[key] = equilibrium
        return equilibrium

    def optimize_component_fiscally(
        self,
        component: Mapping[str, float],
        equilibrium_point: EquilibriumPoint,
    ) -> Mapping[str, float]:
        optimized = {}
        total = sum(component.values()) or 1.0
        for name, value in component.items():
            reduction = equilibrium_point.optimal_cost / total
            optimized[name] = max(0.0, value - value * reduction * 0.1)
        optimized["efficiency_gain"] = equilibrium_point.efficiency_score
        return optimized

    def _run_optimization_cycle(
        self, system_components: Sequence[Mapping[str, float]]
    ) -> FiscalOptimizationReport:
        metrics = []
        for idx, component in enumerate(system_components):
            cost = self.measure_component_cost(component)
            value = self.measure_component_value(component)
            metrics.append(
                CostQualityMetric(
                    component=f"component_{idx}",
                    cost=cost,
                    quality=value,
                    benchmark_cost=cost * 0.95,
                    benchmark_quality=value * 0.98,
                )
            )
        optimizer = EquilibriumOptimizer(self.cost_quality_engine)
        return optimizer.optimize(metrics)

    def execute_fiscal_optimization_cycle(self, system_components: Sequence[Mapping[str, float]]) -> FiscalOptimizationReport:
        signature = self._components_signature(system_components)
        cached = self._optimization_cache.get(signature)
        if cached is not None:
            self.performance_monitor.record_cache_event("optimization_cycle", True)
            return cached

        self.performance_monitor.record_cache_event("optimization_cycle", False)
        report = self.performance_monitor.time_call(
            "optimization_cycle", lambda: self._run_optimization_cycle(system_components)
        )
        self._optimization_cache[signature] = report
        self._lazy_results[signature] = report
        return report

    # Forecasting ----------------------------------------------------------
    def forecast_budget_needs(self, roadmap: StrategicRoadmap) -> Mapping[str, float]:
        return self.budget_intelligence.forecast_budget_needs(roadmap)

    def identify_future_savings(self, roadmap: StrategicRoadmap) -> Mapping[str, float]:
        return self.budget_intelligence.identify_future_savings(roadmap)

    def assess_future_fiscal_risks(self, roadmap: StrategicRoadmap) -> Mapping[str, float]:
        return self.budget_intelligence.assess_future_fiscal_risks(roadmap)

    def generate_fiscal_strategies(self, roadmap: StrategicRoadmap) -> Sequence[str]:
        return self.budget_intelligence.generate_fiscal_strategies(roadmap)

    def forecast_budget_needs_with_accuracy(self, roadmap: StrategicRoadmap) -> FiscalForecast:
        return self.budget_intelligence.predictive_budget_forecasting(roadmap)

    def predictive_fiscal_forecasting(self, strategic_roadmap: StrategicRoadmap) -> FiscalForecast:
        return self.budget_intelligence.predictive_budget_forecasting(strategic_roadmap)

    # Resource orchestration ----------------------------------------------
    def calculate_optimal_allocation(self, fiscal_framework: Mapping[str, float]) -> Mapping[str, float]:
        signature = str(self._mapping_signature(fiscal_framework))
        cached = self._allocation_cache.get(signature)
        if cached is not None:
            self.performance_monitor.record_cache_event("resource_allocation", True)
            return cached
        self.performance_monitor.record_cache_event("resource_allocation", False)
        allocation = self.resource_orchestrator.calculate_optimal_allocation(fiscal_framework)
        self._allocation_cache[signature] = allocation
        return allocation

    def generate_orchestration_plan(self, resource_allocation: Mapping[str, float]):
        return self.resource_orchestrator.generate_orchestration_plan(resource_allocation)

    def get_current_resource_map(self) -> Mapping[str, float]:
        return self.resource_orchestrator.get_current_resource_map()

    def execute_resource_transfer(
        self,
        optimization_plan: ResourceRecommendationSet | Mapping[str, float] | Sequence[str],
    ) -> ReallocationReport:
        if isinstance(optimization_plan, ResourceRecommendationSet):
            return self.resource_orchestrator.execute_reallocation_plan(optimization_plan)
        if isinstance(optimization_plan, Mapping):
            snapshots = [
                ResourceSnapshot(
                    model_name=name,
                    cpu_hours=value,
                    gpu_hours=value,
                    memory_gb=value,
                    throughput=value,
                    performance_score=value,
                )
                for name, value in optimization_plan.items()
            ]
            recommendations = self.resource_orchestrator.analyse_performance(snapshots)
            return self.resource_orchestrator.execute_reallocation_plan(recommendations)
        if isinstance(optimization_plan, Sequence):
            return self.resource_orchestrator.execute_reallocation_plan(
                ResourceRecommendationSet(recommendations=[])
            )
        return ReallocationReport(resources_moved=[], efficiency_gain=0.0, risk_assessment={})

    def monitor_resource_telemetry(self, telemetry: ResourceTelemetryBatch) -> ReallocationReport:
        snapshots = [
            ResourceSnapshot(
                model_name=item.model_name,
                cpu_hours=item.cpu_hours,
                gpu_hours=item.gpu_hours,
                memory_gb=item.memory_gb,
                throughput=item.throughput,
                performance_score=item.throughput / (item.cpu_hours + item.gpu_hours + 1),
            )
            for item in telemetry.telemetry
        ]
        self.resource_orchestrator.load_history(snapshots)
        recommendations = self.resource_orchestrator.analyse_performance(snapshots)
        return self.resource_orchestrator.execute_reallocation_plan(recommendations)

    # ROI -----------------------------------------------------------------
    def establish_roi_intelligence(self, data: Mapping[str, tuple[float, float]], thresholds: Mapping[str, float]):
        return self.value_return.generate_report(data, thresholds)

    # Ledger ---------------------------------------------------------------
    def record_spend(self, phase: str, amount: float, description: str) -> None:
        entry = LedgerEntry(timestamp=datetime.utcnow(), phase=phase, amount=amount, description=description)
        self.fiscal_ledger.record_entry("enterprise", entry)

    def ledger_health(self) -> LedgerHealth:
        return self.fiscal_ledger.health()

    # Integration ----------------------------------------------------------
    def initialize_adapters(self, models: Sequence[str]) -> IntegrationSummary:
        adapters = []
        for model in models:
            adapters.append(
                IntegrationAdapter(
                    model_name=model,
                    adapter_type="api",
                    configuration={"endpoint": f"/api/{model}"},
                    health="green",
                )
            )
        return IntegrationSummary(adapters=adapters, overall_health="green", outstanding_actions=[])

    def adapt_model(self, model_name: str) -> IntegrationAdapterReport:
        return IntegrationAdapterReport(
            model_name=model_name,
            handshake_successful=True,
            interface_details={"version": "1.0"},
            cost_projection=100.0,
            quality_projection=0.95,
        )

    # Oversight ------------------------------------------------------------
    def evaluate_phase(
        self,
        phase_name: str,
        strategic_score: float,
        fiscal_score: float,
        budget: float,
    ) -> OversightRecord:
        approved = strategic_score > 0.75 and fiscal_score > 0.7
        commentary = "Approved" if approved else "Requires review"
        record = OversightRecord(
            phase=phase_name,
            approved=approved,
            strategic_score=strategic_score,
            fiscal_score=fiscal_score,
            budget_consumed=budget,
            commentary=commentary,
        )
        self._oversight_records.append(record)
        return record

    def compile_oversight_interface(self, summary: OversightSummary) -> OversightInterface:
        strategic = {record.phase: record.strategic_score for record in summary.records}
        fiscal = {record.phase: record.fiscal_score for record in summary.records}
        impact = {record.phase: record.budget_consumed for record in summary.records}
        return OversightInterface(strategic_report=strategic, fiscal_report=fiscal, business_impact=impact)

    # Viability ------------------------------------------------------------
    def generate_viability_rejection(
        self,
        strategic_analysis: StrategicAnalysis,
        fiscal_framework: FiscalGovernanceFramework,
    ) -> ViabilityReport:
        blockers = [
            "Strategic feasibility below threshold",
            "Projected spend exceeds guardrails",
        ]
        recommendations = [
            "Refine objectives to increase alignment",
            "Revisit fiscal guardrails with leadership",
        ]
        return ViabilityReport(
            feasibility_score=strategic_analysis.feasibility_score,
            fiscal_viability_score=fiscal_framework.total_budget_allocation,
            blockers=blockers,
            recommendations=recommendations,
        )

    # Dual oversight -------------------------------------------------------
    def initialize_dual_oversight(self):
        self._oversight_records.clear()
        return self

    def approve_phase(
        self,
        phase_name: str,
        budget_allocation: float,
        execution_fn: Callable[[], Mapping[str, float]],
    ):
        result = execution_fn()
        record = self.evaluate_phase(phase_name, 0.8, 0.85, budget_allocation)
        self.fiscal_monitor.capture_signal(
            MonitoringSignal(signal_name=phase_name, value=budget_allocation, status="normal")
        )
        return {"result": result, "oversight": record}

    def get_strategic_report(self) -> Mapping[str, float]:
        summary = self.fiscal_monitor.summarize_oversight(self._oversight_records)
        return {"strategic_alignment": summary.strategic_average}

    def get_fiscal_report(self) -> Mapping[str, float]:
        summary = self.fiscal_monitor.summarize_oversight(self._oversight_records)
        health = self._latest_dashboard.fiscal_health_score if self._latest_dashboard else 0.0
        return {
            "fiscal_alignment": summary.fiscal_average,
            "fiscal_health": health,
        }

    def calculate_business_impact(self) -> Mapping[str, float]:
        summary = self.fiscal_monitor.summarize_oversight(self._oversight_records)
        return {"total_budget_consumed": summary.total_budget_consumed}


