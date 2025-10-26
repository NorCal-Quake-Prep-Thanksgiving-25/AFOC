"""Structured audit logging utilities for AFOC."""

from __future__ import annotations

import hashlib  # Security: strong hash defends against tampering detection collisions.
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

from ..credentials import AFOCSecretsManager


class AuditLogger:
    """Writes append-only audit events with integrity digests."""

    def __init__(self, log_path: str | Path | None = None) -> None:
        self._secrets = AFOCSecretsManager()
        secret = self._secrets.require_secret("AUDIT_HMAC_SECRET")
        self._hmac_key = secret.encode(
            "utf-8"
        )  # Security: encode once to avoid repeated conversions.
        path = Path(log_path or "logs/audit.log")
        path.parent.mkdir(parents=True, exist_ok=True)
        self._logger = logging.getLogger("AFOC.Audit")
        if not any(isinstance(handler, RotatingFileHandler) for handler in self._logger.handlers):
            handler = RotatingFileHandler(path, maxBytes=1_000_000, backupCount=5)
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)
        self._logger.setLevel(logging.INFO)
        self._chain = b""

    def log(
        self, actor: str, action: str, status: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        payload = {
            "actor": actor,
            "action": action,
            "status": status,
            "metadata": metadata or {},
        }
        json_payload = json.dumps(payload, sort_keys=True)
        digest = hashlib.sha256(
            self._hmac_key + self._chain + json_payload.encode("utf-8")
        ).hexdigest()
        entry = {"payload": payload, "digest": digest}
        self._logger.info(json.dumps(entry))
        self._chain = digest.encode(
            "utf-8"
        )  # Security: chaining digests exposes tampering attempts.
