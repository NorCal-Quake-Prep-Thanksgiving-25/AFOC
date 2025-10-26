"""Test configuration for the AFOC intelligence suite."""

from __future__ import annotations

import hashlib  # Security: test harness mirrors production hashing to exercise hardened paths.
import json
import os
import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def pytest_configure() -> None:
    os.environ.setdefault(
        "AFOC_APP_SECRET", "test-secret"
    )  # Security: ensures JWT signing key exists for all tests.
    os.environ.setdefault(
        "AFOC_AUDIT_HMAC_SECRET", "audit-secret"
    )  # Security: audit logger requires deterministic secret.
    default_users = {
        "admin": {
            "password_sha256": hashlib.sha256(b"changeme").hexdigest(),
            "roles": ["admin", "analyst", "viewer"],
        }
    }
    os.environ.setdefault(
        "AFOC_USERS_JSON", json.dumps(default_users)
    )  # Security: populates registry for auth flows.
