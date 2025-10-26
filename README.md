# Autonomous Fiscal Orchestration Core (AFOC)

The Autonomous Fiscal Orchestration Core is a composable mesh of budgeting, forecasting, ROI,
and security agents designed for enterprise-grade fiscal command-and-control. The latest
release elevates the platform to a "God-tier" orchestration system with real integrations,
self-learning intelligence, and hardened governance.

## Highlights

| Capability | What changed | Value |
|------------|--------------|-------|
| **Composable Intelligence Core** | Agents now coordinate through a latency-aware async bus with plugin registration. | 10× maintainability; hot-swappable connectors. |
| **Live Integrations** | AWS Cost Explorer, Azure Cost Management, GCP Billing, GitHub, Datadog, Grafana, OpenAI and Anthropic usage APIs (with graceful fallbacks). | Pull real spend, telemetry, and LLM bills into the data fabric. |
| **Predictive Intelligence** | Bayesian posterior tracking + statsmodels seasonal smoothing, Isolation Forest anomalies, reinforcement allocation. | Forecast accuracy improvements and automated guardrail tuning. |
| **Quantum Optimisation** | Optional PennyLane/Qiskit solvers with quantum-inspired fallbacks drive ROI refinements. | Higher-confidence budget actions with explainable quantum summaries. |
| **Security & DevOps** | GitHub governance, CodeQL, Dependabot, signed commits, security scanner CLI. | Enterprise-grade compliance posture. |
| **Experience Layer** | FastAPI façade, GraphQL router, Streamlit dashboard, expanded CLI/overview tooling. | API, automation, operator visibility, and executive dashboards. |
| **Alerts & Reporting** | Slack/email dispatchers, guardrail breach telemetry, and notebook-driven PDF export. | CFO-ready insights and shareable executive artefacts. |

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .[ml,integrations,quantum]
pip install -r requirements-dev.txt
```

Run the integrated smoke tests (coverage configuration lives in `.coveragerc`):

```bash
pytest -q --maxfail=1 --cov=afoc
ruff check .
black --check .
mypy afoc
bandit -r afoc
```

## Command-Line Interface

```bash
python -m afoc.cli allocate --total 250000 --targets architecture:0.4 implementation:0.35 optimization:0.25
python -m afoc.cli forecast --history 900 950 1000 1100 1200
python -m afoc.cli optimize --rewards 0.1 0.9 0.3 --quantum-only
python -m afoc.cli audit
python -m afoc.cli health
python -m afoc.cli ingest --records analytics:1000 marketing:750 --source quickstart
```

## API & Dashboard

- `afoc.api.build_api()` exposes a FastAPI app with `/allocate`, `/forecast`, `/optimize`, `/optimize/quantum`, and `/audit` endpoints.
- `afoc.graphql.build_graphql_router()` publishes the same capabilities through a GraphQL schema.
- `afoc.dashboard.launch_streamlit_dashboard()` renders the Streamlit UI (run via `streamlit run -m afoc.dashboard.streamlit_app`).
- `python -m afoc.tools.overview --preview` prints a real-time project inventory.

### Authentication & Alerts

- Define `AFOC_APP_SECRET`, `AFOC_AUDIT_HMAC_SECRET`, and `AFOC_USERS_JSON` (SHA-256 hashed passwords + role lists) before starting the API.
- Obtain a JWT with `POST /auth/login` and send `Authorization: Bearer <token>` for `/allocate`, `/forecast`, `/optimize`, `/audit`, `/ingest`, and `/optimize/quantum`.
- Configure `AFOC_SLACK_WEBHOOK` or `AFOC_SMTP_*` / `AFOC_ALERT_RECIPIENTS` to receive anomaly and security alerts via Slack or email.
- `python -m afoc.cli audit` and Streamlit dashboards surface guardrail breaches with the same alerting backends; every action is logged through the tamper-evident audit logger.

## Demo Notebook & Reporting

- `demo.ipynb` walks through the six-model workflow and generates a shareable PDF (text fallback when `fpdf` is not installed).
- Programmatic export is available via `from afoc.tools import export_pdf_summary`.

## Data Fabric & Persistence

- `afoc.data.DataFabric` now supports SQLAlchemy-powered relational stores, Redis caches, ingestion pipelines with retry/backoff, **and a durable job queue with audit logging** for idempotent background processing.
- Built-in multi-tenant isolation stores every spend record with a tenant namespace, per-tenant encryption keys, and append-only audit trails for compliance evidence.
- Secrets resolve through `afoc.credentials` providers (environment, keyring, **cloud KMS decryptor**, composite) for zero-trust deployments.
- Use `core.ingest_collector_payload` to persist plugin data directly into the shared store, and `core.monitor_fiscal_operations` to auto-enqueue reconciliation jobs per tenant.
- Health checks expose relational/cache/encryption status for observability and compliance dashboards.

## Integrations

| Domain | Connector | Notes |
|--------|-----------|-------|
| Cloud Spend | `AWSCostCollector`, `AzureCostCollector`, `GCPCostCollector` | Native SDK calls with exponential backoff, pagination, and idempotent BigQuery jobs; synthetic fallback when credentials are absent. |
| LLM Usage | `OpenAIUsageCollector`, `AnthropicUsageCollector` | Backoff-aware REST clients with 429 retries and deterministic fallback when keys are missing. |
| DevOps | `GitHubCollector`, `DatadogCollector`, `GrafanaCollector` | Fetches live metrics when tokens are provided, otherwise reverts to deterministic synthetic values. |

## Intelligence Stack

| Component | Description |
|-----------|-------------|
| Bayesian forecaster | Normal-inverse-gamma updates with posterior history and multi-step forecasting logged to MLflow when available. |
| Statsmodels seasonal layer | Optional exponential smoothing for seasonal workloads. |
| Isolation Forest detector | ML-based anomaly detection when scikit-learn is available. |
| Reinforcement allocator | Policy-gradient style reinforcement learning for ROI optimization. |
| Quantum optimiser | `afoc.intelligence.quantum.QuantumOptimizer` selects Qiskit/PennyLane backends with quantum-inspired softmax fallback. |
| ML lifecycle | `afoc.ml.lifecycle` integrates optional MLflow tracking and diagnostics logging. |

## Governance & Security

- `.github/workflows/ci.yml` enforces lint, type, security, and coverage checks.
- CodeQL + Dependabot pipelines guard the supply chain.
- CI publishes a CycloneDX SBOM artifact and release workflow signs wheels with Sigstore.
- `security/` package includes pre-push scanning, obfuscation, auditing, and repository hardening helpers.

## Testing

The project ships with regression tests for agents, integrations, and event-bus metrics. Add new
tests under `tests/` and ensure coverage remains above 70% (CI gate) with a roadmap to 90%+.

## Optional Extras

Install with extras to enable live connectors:

```bash
pip install afoc[ml]
pip install afoc[integrations]
pip install afoc[data]
pip install afoc[observability]
pip install afoc[quantum]
pip install afoc[reports]

## Six-Model Integration Flow

```
User Request
   ↓
Strategic Analyst → Strategic Report
   ↓
Autonomous Fiscal Orchestration Core → Fiscal Framework (Budget, Constraints)
   ↓
Senior Manager → Task Distribution Plan
   ↓
Architect → Technical Blueprint
   ↓
Coder → Implementation
   ↓
Optimizer → Performance + Cost-Quality Optimization
   ↓
Final System → Validated + Audited + Efficient
```

Each layer feeds the next with structured intelligence, forming a self-governing enterprise AI
capable of delivering optimised systems end-to-end with quantum-backed fiscal certainty.

Refer to `GOVERNANCE.md` and `CONTRIBUTING.md` for contribution workflows, branch protection, and
security expectations.

