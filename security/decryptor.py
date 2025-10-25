"""Runtime utilities for decrypting secure environment variables."""

from __future__ import annotations

import base64
import json
import logging
from typing import Mapping


LOGGER = logging.getLogger("SecurityDecryptor")


def decrypt_secrets(encrypted_blob: str | None) -> Mapping[str, str]:
    """Decrypt an encrypted blob of secrets.

    The production system would call into a hardware security module. For the
    reference implementation we expect the blob to be a base64 encoded JSON
    document so developers can exercise the workflow locally.
    """

    if not encrypted_blob:
        LOGGER.debug("No encrypted blob provided; returning empty secret map.")
        return {}

    try:
        decoded = base64.b64decode(encrypted_blob)
        secrets = json.loads(decoded.decode("utf-8"))
        LOGGER.debug("Decrypted %d secrets from secure blob.", len(secrets))
        return secrets
    except Exception as exc:  # pragma: no cover - defensive guardrail
        LOGGER.warning("Failed to decrypt secrets: %%s", exc)
        return {}
