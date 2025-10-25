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
| **Security & DevOps** | GitHub governance, CodeQL, Dependabot, signed commits, security scanner CLI. | Enterprise-grade compliance posture. |
| **Experience Layer** | FastAPI façade, GraphQL router, CLI commands, overview tooling. | API, automation, and operator visibility. |

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .[ml,integrations]
pip install -r requirements-dev.txt
```

Run the integrated smoke tests:

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
python -m afoc.cli optimize --rewards 0.1 0.9 0.3
```

## API & Dashboard

- `afoc.api.build_api()` exposes a FastAPI app with `/allocate`, `/forecast`, `/optimize`, and `/audit` endpoints.
- `afoc.graphql.build_graphql_router()` publishes the same capabilities through a GraphQL schema.
- `python -m afoc.tools.overview --preview` prints a real-time project inventory.

## Integrations

| Domain | Connector | Notes |
|--------|-----------|-------|
| Cloud Spend | `AWSCostCollector`, `AzureCostCollector`, `GCPCostCollector` | Uses native SDKs with synthetic fallback when credentials are absent. |
| LLM Usage | `OpenAIUsageCollector`, `AnthropicUsageCollector` | Pulls token + cost summaries via REST; masks API keys through env vars. |
| DevOps | `GitHubCollector`, `DatadogCollector`, `GrafanaCollector` | Fetches live metrics when tokens are provided, otherwise reverts to deterministic synthetic values. |

## Intelligence Stack

| Component | Description |
|-----------|-------------|
| Bayesian forecaster | Normal-inverse-gamma updates with posterior history and multi-step forecasting. |
| Statsmodels seasonal layer | Optional exponential smoothing for seasonal workloads. |
| Isolation Forest detector | ML-based anomaly detection when scikit-learn is available. |
| Reinforcement allocator | Policy-gradient style reinforcement learning for ROI optimization. |

## Governance & Security

- `.github/workflows/ci.yml` enforces lint, type, security, and coverage checks.
- CodeQL + Dependabot pipelines guard the supply chain.
- `security/` package includes pre-push scanning, obfuscation, auditing, and repository hardening helpers.

## Testing

The project ships with regression tests for agents, integrations, and event-bus metrics. Add new
tests under `tests/` and ensure coverage remains above 70% (CI gate) with a roadmap to 90%+.

## Optional Extras

Install with extras to enable live connectors:

```bash
pip install afoc[ml]
pip install afoc[integrations]
```

Refer to `GOVERNANCE.md` and `CONTRIBUTING.md` for contribution workflows, branch protection, and
security expectations.

