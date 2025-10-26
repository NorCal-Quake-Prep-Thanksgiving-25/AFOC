# Governance Overview

This repository operates under a zero-trust posture tailored for commercial IP valued at $25M+. The
following controls are enforced:

- **Branch protection**: `main` requires signed commits, conversation resolution, and two CODEOWNER
  approvals. Only the designated owner can push directly.
- **Required checks**: CI (lint, type check, tests, bandit) and CodeQL must succeed before merge.
- **Security automation**: Dependabot, secret scanning, and pre-push tooling guard against leakage.
- **Documentation**: Contributors must follow `CONTRIBUTING.md` and the PR template.

Refer to `CONTRIBUTING.md` for the prioritised hardening roadmap and local workflow.
