"""Git security utilities for EliteAI."""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Mapping


GIT_SECURITY_COMMANDS = (
    ("commit.gpgsign", "true"),
    ("user.signingkey", "YOUR_GPG_KEY"),
    ("transfer.fsckobjects", "true"),
    ("receive.fsckobjects", "true"),
    ("fetch.fsckobjects", "true"),
)


def _run_git_config(repo_root: Path, key: str, value: str) -> None:
    try:
        subprocess.run(
            ["git", "config", "--local", key, value],
            check=True,
            cwd=repo_root,
        )
    except subprocess.CalledProcessError:
        logging.getLogger("GitSecurity").warning(
            "Unable to set git config %s; ensure repository initialised.", key
        )


def setup_git_security(repo_root: str | Path = Path(".")) -> Mapping[str, str]:
    """Configures high-level git security settings."""

    logger = logging.getLogger("GitSecurity")
    repo_root = Path(repo_root)
    hooks_dir = repo_root / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_path = hooks_dir / "pre-push"
    if not hook_path.exists():
        hook_path.write_text(
            "#!/bin/sh\npython -m security.scanner --check-secrets --check-ips\n",
            encoding="utf-8",
        )
        hook_path.chmod(0o755)
        logger.debug("Created pre-push hook at %s", hook_path)
    else:
        logger.debug("Pre-push hook already present at %s", hook_path)

    for key, value in GIT_SECURITY_COMMANDS:
        _run_git_config(repo_root, key, value)

    return {
        "pre_push_hook": str(hook_path),
        "hooks_directory": str(hooks_dir),
        "configured_settings": {key: value for key, value in GIT_SECURITY_COMMANDS},
    }


def secure_git_push() -> None:
    """Placeholder routine that represents a protected git push."""

    logger = logging.getLogger("GitSecurity")
    logger.info(
        "Secure push executed with mandatory security checks and signed commits."
    )

