"""Core dataclasses shared across the Autonomous Fiscal Orchestration Core."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Mapping, Sequence, Tuple


# ---------------------------------------------------------------------------
# Fiscal governance primitives
# ---------------------------------------------------------------------------


@dataclass
class FiscalGuardrails:
    maximum_allocation: float
    minimum_quality_threshold: float
    risk_tolerance: float
    escalation_threshold: float
    notes: str = ""

    def describe(self) -> str:
        return (
            f"Guardrails(max={self.maximum_allocation:.2f}, quality>={self.minimum_quality_threshold:.2f}, "
            f"risk={self.risk_tolerance:.2f})"
        )


@dataclass
class FiscalGovernanceFramework:
    total_budget_allocation: float
    budget_distribution: Mapping[str, float]
    fiscal_guardrails: FiscalGuardrails
    cost_quality_ratios: Mapping[str, float]
    resource_efficiency_targets: Mapping[str, float]
    roi_thresholds: Mapping[str, float]
    spending_velocity_controls: Mapping[str, float]
    auto_reallocation_triggers: Mapping[str, float]
    fiscal_health_monitors: Mapping[str, float]
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def summarize(self) -> str:
        distribution = ", ".join(
            f"{phase}:{amount:.2f}" for phase, amount in self.budget_distribution.items()
        )
        return f"Budget={self.total_budget_allocation:.2f}; Distribution=[{distribution}]"


# ---------------------------------------------------------------------------
# Strategic artefacts
# ---------------------------------------------------------------------------


@dataclass
class StrategicRequest:
    objective: str
    constraints: Mapping[str, float]
    expected_roi: float


@dataclass
class StrategicAnalysis:
    feasibility_score: float
    alignment_vector: Mapping[str, float]
    narrative: str


@dataclass
class StrategicPlan:
    architecture_budget: float
    implementation_budget: float
    optimization_budget: float
    architectural_tasks: Sequence[str]
    implementation_tasks: Sequence[str]
    optimization_tasks: Sequence[str]
    technical_constraints: Sequence[str]
    fiscal_constraints: Mapping[str, float]
    fiscal_guidelines: Mapping[str, float]
    performance_slas: Mapping[str, float]
    roi_targets: Mapping[str, float]
    coding_standards: Sequence[str]


@dataclass
class StrategicRoadmap:
    milestones: Sequence[str]
    fiscal_targets: Mapping[str, float]
    scenario_assumptions: Mapping[str, float]
    growth_projection: float


@dataclass
class FiscalCognitiveMap:
    resource_flow_dynamics: Mapping[str, float]
    cost_quality_tradeoffs: Mapping[str, Tuple[float, float]]
    investment_optimization: Mapping[str, float]
    risk_adjusted_returns: Mapping[str, float]

    def prioritized_streams(self) -> Sequence[str]:
        return sorted(
            self.resource_flow_dynamics,
            key=lambda name: self.risk_adjusted_returns.get(name, 0.0),
            reverse=True,
        )


# ---------------------------------------------------------------------------
# Monitoring and oversight
# ---------------------------------------------------------------------------


@dataclass
class MonitoringSignal:
    signal_name: str
    value: float
    status: str


@dataclass
class MonitoringSnapshot:
    signals: Sequence[MonitoringSignal]
    generated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PolicyAdjustment:
    policy_name: str
    adjustment_value: float
    justification: str
    effective_date: datetime


@dataclass
class AdaptivePolicyState:
    policies: Sequence[PolicyAdjustment]
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PolicyBreach:
    policy_name: str
    severity: str
    deviation: float
    remediation_steps: Sequence[str]


@dataclass
class PolicyBreachReport:
    breaches: Sequence[PolicyBreach]
    generated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class OversightRecord:
    phase: str
    approved: bool
    strategic_score: float
    fiscal_score: float
    budget_consumed: float
    commentary: str


# ---------------------------------------------------------------------------
# Commercial expansion artefacts
# ---------------------------------------------------------------------------


@dataclass
class QuantumROIReport:
    financial_metrics: Mapping[str, float]
    competitive_metrics: Mapping[str, str]
    future_metrics: Mapping[str, str]

    def blended_roi(self) -> float:
        cost_savings = self.financial_metrics.get("cost_savings", 0.0)
        revenue = self.financial_metrics.get("revenue_acceleration", 0.0)
        risk = self.financial_metrics.get("risk_mitigation_value", 0.0)
        option_value = self.financial_metrics.get("strategic_option_value", 0.0)
        return cost_savings + revenue + risk + option_value


@dataclass
class CompetitiveGapAnalysis:
    first_mover_advantage: str
    operational_superiority: str
    strategic_positioning: str


@dataclass
class QuantumOptimizationSummary:
    """Snapshot of the quantum or quantum-inspired optimization outcome."""

    backend: str
    method: str
    shots: int
    objective_value: float
    recommended_action: str | None
    converged: bool
    state_probabilities: Mapping[str, float]

    def as_payload(self) -> Dict[str, object]:
        """Return a JSON-serialisable payload for API and CLI surfaces."""

        return {
            "backend": self.backend,
            "method": self.method,
            "shots": self.shots,
            "objective_value": self.objective_value,
            "recommended_action": self.recommended_action,
            "converged": self.converged,
            "state_probabilities": dict(self.state_probabilities),
        }


@dataclass
class SalesPipeline:
    lead_generation: int
    personalized_outreach: int
    meeting_scheduling: int
    proposal_generation: int
    contract_negotiation: int
    onboarding: int

    def conversion_rate(self) -> float:
        return (self.contract_negotiation / self.lead_generation) if self.lead_generation else 0.0


@dataclass
class DocumentationSuite:
    technical_white_paper: str
    business_value_proposition: str
    competitive_analysis: str
    case_study_library: Sequence[str]
    implementation_guides: Sequence[str]
    security_compliance: Sequence[str]

    def summary(self) -> str:
        return (
            f"Whitepaper pages: {len(self.technical_white_paper.splitlines())}, "
            f"Case studies: {len(self.case_study_library)}"
        )


@dataclass
class PersonalizedPitchDeck:
    executive_summary: str
    technical_details: str
    financial_analysis: str
    implementation_timeline: str


@dataclass
class PerformanceGuarantees:
    uptime: str
    response_time: str
    scalability: str
    security: str
    support: str


@dataclass
class FullyOperationalCommercialPlatform:
    core_ai: object
    business_operations: Mapping[str, object]
    revenue_ready: bool
    valuation: str
    time_to_market: str

    def status_report(self) -> str:
        readiness = "ready" if self.revenue_ready else "in-progress"
        return f"Platform is {readiness} with valuation {self.valuation}"


@dataclass
class OversightSummary:
    records: Sequence[OversightRecord]
    strategic_average: float
    fiscal_average: float
    total_budget_consumed: float


@dataclass
class OversightInterface:
    strategic_report: Mapping[str, float]
    fiscal_report: Mapping[str, float]
    business_impact: Mapping[str, float]


@dataclass
class EnterpriseDelivery:
    technical_components: Mapping[str, Mapping[str, float]]
    strategic_analysis: Mapping[str, float]
    fiscal_performance: Mapping[str, float]
    business_impact_metrics: Mapping[str, float]


@dataclass
class SpendingVelocity:
    phase: str
    velocity: float
    alert_level: str


@dataclass
class FiscalOperationsDashboard:
    real_time_spending: Mapping[str, float]
    cost_performance_metrics: Mapping[str, float]
    budget_burn_rate: Mapping[str, float]
    fiscal_health_score: float
    recommended_optimizations: Sequence[str]
    resource_reallocation_directives: Mapping[str, float]
    cost_quality_adjustments: Mapping[str, float]
    cost_per_unit: Mapping[str, float]
    quality_scores: Mapping[str, float]
    policy_violation_mttr_hours: float
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def summary(self) -> str:
        def burn_score(phase: str) -> float:
            return self.budget_burn_rate.get(phase, 0.0)

        top_phase = max(self.budget_burn_rate, key=burn_score, default="n/a")
        cost_values = list(self.cost_per_unit.values())
        avg_cost = sum(cost_values) / max(len(cost_values), 1)
        return (
            f"Health={self.fiscal_health_score:.2f}; Highest burn={top_phase}; "
            f"Avg cost/unit={avg_cost:.2f}; MTTR={self.policy_violation_mttr_hours:.1f}h"
        )


# ---------------------------------------------------------------------------
# Cost-quality equilibrium models
# ---------------------------------------------------------------------------


@dataclass
class CostQualityDirective:
    component: str
    action: str
    expected_gain: float
    confidence: float


@dataclass
class CostQualityPlan:
    directives: Sequence[CostQualityDirective]
    optimal_points: Mapping[str, float]
    required_actions: Sequence[str]
    expected_improvements: Mapping[str, float]
    generated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CostQualitySnapshot:
    components: Mapping[str, Tuple[float, float]]
    equilibrium: Mapping[str, float]
    anomalies: Sequence[str]


@dataclass
class CostQualitySnapshotEnvelope:
    snapshot: CostQualitySnapshot
    directives: CostQualityPlan


@dataclass
class QualitySignal:
    component: str
    metric: str
    value: float
    target: float


@dataclass
class QualitySignalBatch:
    signals: Sequence[QualitySignal]

    def below_target(self) -> Sequence[QualitySignal]:
        return [signal for signal in self.signals if signal.value < signal.target]


@dataclass
class CostDrift:
    component: str
    observed_cost: float
    expected_cost: float
    deviation: float


@dataclass
class CostDriftAnalysis:
    drifts: Sequence[CostDrift]
    recommendations: Sequence[str]


@dataclass
class EquilibriumPoint:
    optimal_cost: float
    optimal_quality: float
    efficiency_score: float
    explanation: str


@dataclass
class FiscalEquilibriumState:
    current_equilibrium: Mapping[str, float]
    optimal_targets: Mapping[str, float]
    adjustment_actions: Sequence[str]
    efficiency_gains: Mapping[str, float]

    def needs_intervention(self, threshold: float = 0.1) -> bool:
        for component, current in self.current_equilibrium.items():
            target = self.optimal_targets.get(component, current)
            if target == 0:
                continue
            deviation = abs(current - target) / target
            if deviation > threshold:
                return True
        return False


@dataclass
class OptimizationRecord:
    component_name: str
    previous_cost: float
    previous_value: float
    new_cost: float
    new_value: float
    equilibrium: EquilibriumPoint
    reasoning: str


@dataclass
class FiscalOptimizationReport:
    optimizations: list[OptimizationRecord] = field(default_factory=list)

    def add_optimization(self, record: OptimizationRecord) -> None:
        self.optimizations.append(record)

    def total_savings(self) -> float:
        return sum(item.previous_cost - item.new_cost for item in self.optimizations)


# ---------------------------------------------------------------------------
# Forecasting and budget intelligence
# ---------------------------------------------------------------------------


@dataclass
class FiscalForecast:
    projected_budget_requirements: Mapping[str, float]
    future_cost_optimization_opportunities: Mapping[str, float]
    fiscal_risk_assessment: Mapping[str, float]
    recommended_fiscal_strategies: Sequence[str]


@dataclass
class ForecastAccuracy:
    target: float
    actual: float
    confidence: float

    def error_margin(self) -> float:
        if self.target == 0:
            return 0.0
        return abs(self.target - self.actual) / self.target


@dataclass
class ForecastAudit:
    forecast_id: str
    accuracy: float
    variance: float
    commentary: str


@dataclass
class ForecastAuditTrail:
    audits: Sequence[ForecastAudit]


@dataclass
class ForecastDrift:
    metric: str
    predicted: float
    actual: float
    deviation: float


@dataclass
class ForecastDriftReport:
    drifts: Sequence[ForecastDrift]
    commentary: Sequence[str]


@dataclass
class BudgetScenario:
    scenario_name: str
    baseline_allocation: Mapping[str, float]
    stress_tests: Mapping[str, float]
    success_probability: float
    commentary: str


@dataclass
class BudgetInsight:
    title: str
    description: str
    impact: float


@dataclass
class BudgetIntelligenceReport:
    forecasts: Sequence[ForecastAccuracy]
    scenarios: Sequence[BudgetScenario]
    insights: Sequence[BudgetInsight]
    recommendations: Sequence[str]


@dataclass
class AdaptiveBudget:
    baseline: Mapping[str, float]
    adjustments: Mapping[str, float]
    confidence: float


@dataclass
class AdaptiveBudgetOutcome:
    applied_budget: Mapping[str, float]
    rationale: Sequence[str]
    confidence: float


# ---------------------------------------------------------------------------
# Resource orchestration
# ---------------------------------------------------------------------------


@dataclass
class ResourceRecommendation:
    model_name: str
    action: str
    delta: float
    justification: str


@dataclass
class ResourceRecommendationSet:
    recommendations: Sequence[ResourceRecommendation]


@dataclass
class ResourceShift:
    source: str
    destination: str
    amount: float
    justification: str


@dataclass
class ReallocationReport:
    resources_moved: Sequence[ResourceShift]
    efficiency_gain: float
    risk_assessment: Mapping[str, float]


@dataclass
class ResourceOrchestration:
    current_allocation: Mapping[str, float]
    target_allocation: Mapping[str, float]
    transition_strategy: Sequence[str]
    expected_efficiency: Mapping[str, float]


@dataclass
class ResourceTelemetry:
    model_name: str
    cpu_hours: float
    gpu_hours: float
    memory_gb: float
    storage_gb: float
    throughput: float


@dataclass
class ResourceTelemetryBatch:
    telemetry: Sequence[ResourceTelemetry]
    collected_at: datetime = field(default_factory=datetime.utcnow)

    def utilization_summary(self) -> Mapping[str, float]:
        totals = {"cpu_hours": 0.0, "gpu_hours": 0.0, "memory_gb": 0.0, "storage_gb": 0.0}
        for item in self.telemetry:
            totals["cpu_hours"] += item.cpu_hours
            totals["gpu_hours"] += item.gpu_hours
            totals["memory_gb"] += item.memory_gb
            totals["storage_gb"] += item.storage_gb
        return totals


# ---------------------------------------------------------------------------
# Ledger primitives
# ---------------------------------------------------------------------------


@dataclass
class LedgerEntry:
    timestamp: datetime
    phase: str
    amount: float
    description: str


@dataclass
class LedgerSnapshot:
    entries: Sequence[LedgerEntry]
    totals: Mapping[str, float]
    burn_rate: Mapping[str, float]


@dataclass
class LedgerBalance:
    phase: str
    committed: float
    spent: float
    remaining: float


@dataclass
class LedgerHealth:
    balances: Sequence[LedgerBalance]
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def total_remaining(self) -> float:
        return sum(balance.remaining for balance in self.balances)


@dataclass
class LedgerSyncStatus:
    ledger_name: str
    synced: bool
    entries_processed: int
    last_sync: datetime


@dataclass
class LedgerSyncReport:
    statuses: Sequence[LedgerSyncStatus]


@dataclass
class LedgerException:
    entry: LedgerEntry
    reason: str


@dataclass
class LedgerExceptionReport:
    exceptions: Sequence[LedgerException]


@dataclass
class LedgerReconciliation:
    snapshots: Sequence[LedgerSnapshot]
    discrepancies: Sequence[str]


@dataclass
class SpendingAlert:
    phase: str
    message: str
    severity: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SpendingAlertFeed:
    alerts: Sequence[SpendingAlert]


# ---------------------------------------------------------------------------
# ROI and viability artefacts
# ---------------------------------------------------------------------------


@dataclass
class ROIInsight:
    initiative: str
    cost: float
    benefit: float
    roi: float
    commentary: str


@dataclass
class ROIReport:
    insights: Sequence[ROIInsight]
    aggregate_roi: float
    recommendations: Sequence[str]


@dataclass
class ROIThresholdBreach:
    initiative: str
    threshold: float
    actual: float
    deviation: float


@dataclass
class ROIIntelligence:
    report: ROIReport
    breaches: Sequence[ROIThresholdBreach]


@dataclass
class ViabilityReport:
    feasibility_score: float
    fiscal_viability_score: float
    blockers: Sequence[str]
    recommendations: Sequence[str]


# ---------------------------------------------------------------------------
# Integration artefacts
# ---------------------------------------------------------------------------


@dataclass
class IntegrationAdapter:
    model_name: str
    adapter_type: str
    configuration: Mapping[str, str]
    health: str


@dataclass
class IntegrationAdapterReport:
    model_name: str
    handshake_successful: bool
    interface_details: Mapping[str, str]
    cost_projection: float
    quality_projection: float


@dataclass
class IntegrationSummary:
    adapters: Sequence[IntegrationAdapter]
    overall_health: str
    outstanding_actions: Sequence[str]


# ---------------------------------------------------------------------------
# Security artefacts
# ---------------------------------------------------------------------------


@dataclass
class ProtectionReport:
    """Summarises the protection layers applied to core intellectual property."""

    obfuscated_modules: Sequence[str]
    encrypted_business_logic: str
    legal_headers: str
    watermarking: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def summary(self) -> str:
        modules = ", ".join(self.obfuscated_modules)
        return (
            f"ProtectionReport(modules=[{modules}], encryption={self.encrypted_business_logic}, "
            f"watermark={self.watermarking})"
        )


@dataclass
class SecurityScan:
    """Represents the result of a repository-wide security scan."""

    secrets_detected: Sequence[str]
    ip_exposure: Sequence[str]
    obfuscation_status: bool
    legal_headers: bool
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def all_secure(self) -> bool:
        return (
            not self.secrets_detected
            and not self.ip_exposure
            and self.obfuscation_status
            and self.legal_headers
        )


@dataclass
class CommercialLicense:
    """Details the commercial licensing terms generated for the platform."""

    copyright: str
    restrictions: Sequence[str]
    enforcement: str
    jurisdiction: str


@dataclass
class SecurityDashboard:
    """Aggregated security telemetry for the commercial platform."""

    access_monitoring: str
    leak_detection: str
    legal_enforcement: str
    compliance_tracking: str
    generated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RepositoryHardeningReport:
    """Tracks repository-level hardening actions and status."""

    repository_private: bool
    branch_protection_applied: bool
    signed_commits_required: bool
    security_features: Sequence[str]
    actions_taken: Sequence[str] = field(default_factory=tuple)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def summary(self) -> str:
        features = ", ".join(self.security_features)
        actions = ", ".join(self.actions_taken) if self.actions_taken else "none"
        return (
            "RepositoryHardeningReport("
            f"private={self.repository_private}, "
            f"branch_protection={self.branch_protection_applied}, "
            f"signed_commits={self.signed_commits_required}, "
            f"features=[{features}], actions=[{actions}]"
            ")"
        )


@dataclass
class SecurityAuditResult:
    """Outcome of an end-to-end commercial security audit."""

    scan: SecurityScan
    issues: Sequence[str]
    remediation_actions: Sequence[str]
    generated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def all_secure(self) -> bool:
        return self.scan.all_secure and not self.issues
