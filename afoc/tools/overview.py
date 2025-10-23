"""High-level overview tooling for the EliteAI Enterprise codebase."""
from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Iterable, Sequence

import argparse
import textwrap


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


@dataclass(frozen=True)
class FilePreview:
    """Preview snippet for a file."""

    path: str
    preview: str


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


def generate_system_overview(
    base_dir: str | Path | None = None,
    *,
    key_files: int = 5,
) -> SystemOverview:
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


def _load_preview_text(path: Path, lines: int) -> str:
    try:
        with path.open("r", encoding="utf-8") as stream:
            snippet_lines: list[str] = []
            for _ in range(lines):
                line = stream.readline()
                if not line:
                    break
                snippet_lines.append(line)
    except FileNotFoundError:
        return "<file missing>"
    except UnicodeDecodeError:
        return "<binary content>"
    return "".join(snippet_lines)


def generate_preview_view(
    base_dir: str | Path | None = None,
    *,
    max_files: int = 3,
    lines: int = 8,
) -> list[FilePreview]:
    """Produce previews for the largest Python files in the package."""

    resolved_base = Path(base_dir) if base_dir is not None else Path(__file__).resolve().parents[1]
    python_paths = list(_iter_python_files(resolved_base))
    top_files = _top_n_by_size(python_paths, max_files, resolved_base)

    previews: list[FilePreview] = []
    for info in top_files:
        preview_text = _load_preview_text(resolved_base / info.path, lines)
        previews.append(
            FilePreview(
                path=info.path,
                preview=preview_text,
            )
        )
    return previews


def print_preview_view(
    base_dir: str | Path | None = None,
    *,
    max_files: int = 3,
    lines: int = 8,
) -> list[FilePreview]:
    """Print a preview of the key files and return the structured data."""

    previews = generate_preview_view(base_dir, max_files=max_files, lines=lines)

    if not previews:
        print("=== PREVIEW VIEW ===")
        print("<no python files discovered>")
        return previews

    print("=== PREVIEW VIEW ===")
    for preview in previews:
        print(f"--- {preview.path} (first {lines} lines) ---")
        if preview.preview:
            print(textwrap.indent(preview.preview.rstrip(), "    "))
        else:
            print("    <empty file>")
    return previews


def print_system_overview(
    base_dir: str | Path | None = None,
    *,
    include_preview: bool = False,
    preview_files: int = 3,
    preview_lines: int = 8,
) -> SystemOverview:
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

    if include_preview:
        print_preview_view(
            base_dir,
            max_files=preview_files,
            lines=preview_lines,
        )

    return overview


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect the EliteAI codebase")
    parser.add_argument(
        "--base-dir",
        type=str,
        help="Override the base directory used for inspection",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Include a preview view of the largest Python modules",
    )
    parser.add_argument(
        "--preview-files",
        type=int,
        default=3,
        help="Number of files to preview when --preview is supplied",
    )
    parser.add_argument(
        "--preview-lines",
        type=int,
        default=8,
        help="Number of lines to show for each file preview",
    )

    args = parser.parse_args(argv)

    print_system_overview(
        args.base_dir,
        include_preview=args.preview,
        preview_files=args.preview_files,
        preview_lines=args.preview_lines,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
