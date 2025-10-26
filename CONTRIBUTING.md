# Contributing to AFOC

Thank you for investing in the EliteAI fiscal orchestration platform. This guide summarises the
process required to contribute safely and in line with the DeepSeek governance recommendations.

## Local Environment Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt  # optional runtime deps
pip install -r requirements-dev.txt
```

## Required Checks Before Opening a Pull Request

Run the automated checks locally; they must also pass in CI:

```bash
ruff check .
black --check .
mypy afoc
bandit -r afoc
pytest -q --maxfail=1 --cov=afoc
```

Ensure no secrets or proprietary assets are exposed and keep commits signed (`git commit -S ...`).

## Pull Request Expectations

* Complete the PR template, including the security checklist.
* Link issues or design documents where relevant.
* Request two approvals (one must be a CODEOWNER).
* CI must be green and branch must be up to date with `main`.

## Governance Roadmap

The following plan tracks the remaining hardening work. Revisit after each milestone.

1. **Add CI and enforce it via branch protection** – Complete in this change-set.
2. **Ensure tests exist and CI runs them** – Expand the suite to cover core flows (ETA 2–4 days).
3. **Add formatting, lint, and mypy check** – Implemented here; continue tightening rules as code stabilises.
4. **Add security scans (CodeQL + Bandit) and Dependabot** – Configured here; monitor alerts weekly.
5. **Add docs and CONTRIBUTING, PR template, CODEOWNERS** – Completed; iterate with onboarding feedback.
6. **Improve/expand tests to 90%+ coverage and add integration/contract tests** – Target within 1–3 weeks.
7. **Add release automation and coverage reporting** – Integrate semantic-release and coverage badges (1–2 weeks).
8. **Add observability, monitoring, and stress/perf tests** – Establish benchmarking harness (2–4 weeks).

Measure progress via coverage %, mean time to merge, and security alert MTTR.
