"""High-level overview tooling for the EliteAI Enterprise codebase."""
from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class FileInfo:
    """Lightweight representation of a code file."""

    path: str
    size_bytes: int

    def human_readable_size(self) -> str:
        if self.size_bytes < 1024:
            return f"{self.size_bytes} B"
        if self.size_bytes < 1024 * 1024:
            return f"{self.size_bytes / 1024:.1f} KB"
        return f"{self.size_bytes / (1024 * 1024):.2f} MB"


@dataclass(frozen=True)
class SystemOverview:
    """Aggregated details for quick system inspection."""

    module_paths: Sequence[str]
    key_files: Sequence[FileInfo]
    import_successful: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "module_paths": list(self.module_paths),
            "key_files": [
                {"path": info.path, "size_bytes": info.size_bytes}
                for info in self.key_files
            ],
            "import_successful": self.import_successful,
        }


def _iter_python_files(base_dir: Path) -> Iterable[Path]:
    for path in sorted(base_dir.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        yield path


def _top_n_by_size(paths: Iterable[Path], limit: int, base_dir: Path) -> list[FileInfo]:
    file_infos = [
        FileInfo(path=str(path.relative_to(base_dir)), size_bytes=path.stat().st_size)
        for path in paths
    ]
    file_infos.sort(key=lambda info: info.size_bytes, reverse=True)
    return file_infos[:limit]


def generate_system_overview(base_dir: str | Path | None = None, *, key_files: int = 5) -> SystemOverview:
    """Create a concise overview of the AFoC package structure."""

    resolved_base = Path(base_dir) if base_dir is not None else Path(__file__).resolve().parents[1]
    python_paths = list(_iter_python_files(resolved_base))
    module_paths = [str(path.relative_to(resolved_base)) for path in python_paths[:10]]

    top_files = _top_n_by_size(python_paths, key_files, resolved_base)

    try:
        import_module("afoc.elite_enterprise")
        import_successful = True
    except Exception:
        import_successful = False

    return SystemOverview(
        module_paths=module_paths,
        key_files=top_files,
        import_successful=import_successful,
    )


def print_system_overview(base_dir: str | Path | None = None) -> SystemOverview:
    """Print a human friendly overview and return the structured data."""

    overview = generate_system_overview(base_dir)

    print("=== ELITEAI SYSTEM ANALYSIS ===")
    for path in overview.module_paths:
        print(path)

    print("=== KEY FILES ===")
    for info in overview.key_files:
        print(f"{info.path} ({info.human_readable_size()})")

    print("=== TEST IMPORTS ===")
    if overview.import_successful:
        print("✅ EliteAIEnterprisePro import successful")
    else:
        print("❌ EliteAIEnterprisePro import failed")

    return overview


if __name__ == "__main__":
    print_system_overview()
