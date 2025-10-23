"""Secret scanning utilities to prevent accidental credential leaks."""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Iterable, Sequence


COMMON_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS
    re.compile(r"AIza[0-9A-Za-z\-_]{35}"),  # Google API key
    re.compile(r"sk_[a-zA-Z0-9]{32,}"),  # Generic secret token
    re.compile(r"(?<![A-Z0-9])[A-Z0-9]{32}(?![A-Z0-9])"),  # Uppercase 32-char API keys
)


class SecretScanner:
    """Performs regex-based secret scanning across files."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.logger = logging.getLogger(self.__class__.__name__)

    def _iter_paths(self, include: Sequence[str] | None = None) -> Iterable[Path]:
        include = include or [".py", ".env", ".json"]
        for extension in include:
            yield from self.root.rglob(f"*{extension}")

    def scan_for_secrets(self) -> list[str]:
        findings: list[str] = []
        for path in self._iter_paths():
            try:
                content = path.read_text(encoding="utf-8")
            except OSError:
                continue
            for pattern in COMMON_PATTERNS:
                if pattern.search(content):
                    findings.append(str(path))
                    self.logger.debug("Potential secret detected in %s", path)
                    break
        return sorted(set(findings))

    def scan_paths(self, paths: Sequence[str]) -> list[str]:
        findings: list[str] = []
        for path_str in paths:
            path = Path(path_str)
            try:
                content = path.read_text(encoding="utf-8")
            except OSError:
                continue
            for pattern in COMMON_PATTERNS:
                if pattern.search(content):
                    findings.append(str(path))
                    break
        return sorted(set(findings))

