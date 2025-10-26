# EliteAI Enterprise Security Policy

## Repository Configuration Checklist
- Repository visibility: **PRIVATE** (never make the codebase public).
- Enabled GitHub features: Issues, Projects, Wiki, Discussions.
- Disabled GitHub features: Sponsorships, Merge queue until commercial SLAs finalised.
- Branch protection applied to `main` with two approvals, required status checks, signed commits, and administrator enforcement.
- Only the owner account has push permissions; collaborators are added only after contracts are executed.

## Code Security and Analysis
- Dependency graph, Dependabot alerts, and Dependabot security updates **enabled**.
- Secret scanning with push protection **enabled** for all branches.
- Code scanning and private vulnerability reporting **enabled**.
- Mandatory pre-push security scanning via `python -m security.scanner --check-secrets --check-ips`.
- Automated CI security gate executes `pip-audit`, `safety`, `bandit`, and `pytest` on every push.
- JWT auth tokens are signed with `AFOC_APP_SECRET` and enforced with role-based controls across all FastAPI routes.
- Unified audit logging stores tamper-evident digests secured by `AFOC_AUDIT_HMAC_SECRET`.

## Environment Hygiene
- Secrets stored in `.env.secure` (ignored by git) using encrypted blobs.
- Decrypt secrets at runtime with `security.decryptor.decrypt_secrets`.
- Refresh `.env.secure.template` to onboard new operators without leaking credentials.
- The `AFOCSecretsManager` loads secrets from `.env`, cloud KMS ciphertexts, or keyring without embedding plaintext in code.

## Reporting a Vulnerability
Email security@eliteai.example.com with detailed reproduction steps. We aim to acknowledge reports within 24 hours.

## Supported Versions
Security updates are provided for the current mainline release of the EliteAI Enterprise platform.

## Responsible Disclosure
We request a 14-day disclosure window to investigate and address reported issues before public release.
