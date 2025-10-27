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
   The API enforces an `X-API-Key` header; the default development token is
   `dev-token`. Override `API_TOKENS` in your `.env` file with a comma-separated
   list (optionally append `:role` to assign viewer/analyst/admin roles).

5. Launch the dashboard:
   ```bash
   streamlit run afoc/dashboard/app.py
   ```

6. Try the pre-bundled sample data for an immediate demo:
   ```bash
   curl -H "X-API-Key: dev-token" \
     -F "kind=openai" \
     -F "file=@sample_data/openai_usage_sample.csv" \
     http://localhost:8000/ingest/upload
   ```
   Sample CSVs for OpenAI usage and AWS CUR exports live under `sample_data/`.

## Integrations

- **AWS Cost Explorer** – use `afoc.integrations.aws.CostAnomalyDetector` to pull real billing
  data with retry-aware pagination and feed anomalies back into the orchestration core.
- **AWS EC2 right-sizing** – `afoc.integrations.aws.EC2RightSizer` inspects utilisation metrics
  and produces downsizing recommendations that feed into the optimisation engine.
- **CSV ingestion** – upload usage exports via `/ingest/upload?kind=openai|aws` or by calling
  the loaders directly for bespoke datasets.

The `.env.template` contains placeholders for the required credentials; always manage the real
values outside of the repository (e.g. cloud KMS, Vault, or AWS Secrets Manager).

## Rate Limiting & Auth

- Requests must supply a valid `X-API-Key`. Tokens are configured via
  `API_TOKENS` in the environment (comma-separated). Each key is rate limited to
  `API_RATE_LIMIT` requests per minute (default 120) to protect shared demo
  environments.
- The `/health` endpoint remains unauthenticated for container orchestration
  checks.

## Production Scaling Path

The following enhancements can be layered on without restructuring the codebase:

```yaml
future_enhancements:
  caching: redis
  async_tasks: celery
  orchestration: kubernetes
  infrastructure_as_code: terraform
  dashboards: grafana
```
