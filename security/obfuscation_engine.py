"""Utility routines for lightweight code obfuscation and watermarking."""
from __future__ import annotations

import base64
import hashlib
import logging
from dataclasses import dataclass
from typing import Iterable


@dataclass
class ObfuscationResult:
    """Represents the output of an obfuscation pass."""

    module: str
    digest: str
    watermark: str


class ObfuscationEngine:
    """Applies deterministic transformations to protect sensitive modules."""

    def __init__(self, seed: str = "EliteAI-Obfuscation-Seed") -> None:
        self.seed = seed
        self.logger = logging.getLogger(self.__class__.__name__)

    def _derive_digest(self, module: str, code: str) -> str:
        hasher = hashlib.sha256()
        hasher.update(self.seed.encode("utf-8"))
        hasher.update(module.encode("utf-8"))
        hasher.update(code.encode("utf-8"))
        digest = hasher.hexdigest()
        self.logger.debug("Derived digest for module %s: %s", module, digest)
        return digest

    def obfuscate(self, module: str, code: str) -> str:
        """Returns a reversible obfuscated payload."""

        digest = self._derive_digest(module, code)
        payload = f"{module}:{digest}:{code}"
        obfuscated = base64.b64encode(payload.encode("utf-8")).decode("ascii")
        self.logger.debug("Obfuscated module %s", module)
        return obfuscated

    def watermark(self, module: str, owner: str) -> str:
        """Produces a hidden watermark that can be embedded in binaries."""

        watermark = hashlib.sha1(f"{module}:{owner}:{self.seed}".encode("utf-8")).hexdigest()
        self.logger.debug("Generated watermark for module %s", module)
        return watermark

    def protect_modules(self, modules: Iterable[str]) -> Iterable[ObfuscationResult]:
        for module in modules:
            digest = self._derive_digest(module, module[::-1])
            watermark = self.watermark(module, owner="EliteAI Enterprises")
            yield ObfuscationResult(module=module, digest=digest, watermark=watermark)

