# AFOC Bootstrap

This repository contains a minimal bootstrap for the Autonomous Fiscal Orchestration Core (AFOC).

## Getting Started

1. Create an environment file from the template and supply **your own** secrets:
   ```bash
   cp .env.template .env
   # populate AWS/OpenAI/Stripe keys via your secrets manager – do not commit them
   ```
2. Install dependencies (development extras include linting + tests):
   ```bash
   pip install -e .[dev]
   ```
3. Run the quality gates:
   ```bash
   ruff check .
   black --check .
   mypy afoc
   pytest
   ```
4. Launch the API:
   ```bash
   uvicorn afoc.api.app:create_app --factory
   ```
5. Launch the dashboard:
   ```bash
   streamlit run afoc/dashboard/app.py
   ```

## Integrations

- **AWS Cost Explorer** – use `afoc.integrations.aws.CostAnomalyDetector` to pull real billing
  data with retry-aware pagination and feed anomalies back into the orchestration core.
- **AWS EC2 right-sizing** – `afoc.integrations.aws.EC2RightSizer` inspects utilisation metrics
  and produces downsizing recommendations that feed into the optimisation engine.
- **CSV ingestion** – upload usage exports via `/ingest/upload?kind=openai|aws` or by calling
  the loaders directly for bespoke datasets.

The `.env.template` contains placeholders for the required credentials; always manage the real
values outside of the repository (e.g. cloud KMS, Vault, or AWS Secrets Manager).
