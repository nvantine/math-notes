#!/usr/bin/env python3
"""Synchronize marker-delimited Lean snippets for the Quarto site."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml


class MarkerError(ValueError):
    """Raised when a marker pair is missing or ambiguous."""


class StaleGeneratedFiles(RuntimeError):
    """Raised when check mode finds generated files that need updating."""


@dataclass(frozen=True)
class ExtractedSnippet:
    code: str
    start_line: int
    end_line: int


def extract_marked_region(source: str, label: str) -> ExtractedSnippet:
    """Extract the unique marker-delimited region for ``label``."""
    lines = source.splitlines(keepends=True)
    begin_marker = f"-- MATH_NOTES_BEGIN {label}"
    end_marker = f"-- MATH_NOTES_END {label}"
    begins = [index for index, line in enumerate(lines) if line.strip() == begin_marker]
    ends = [index for index, line in enumerate(lines) if line.strip() == end_marker]

    if not begins or not ends:
        raise MarkerError(f"{label}: missing marker pair")
    if len(begins) != 1 or len(ends) != 1:
        raise MarkerError(f"{label}: expected exactly one marker pair")

    begin, end = begins[0], ends[0]
    if end <= begin:
        raise MarkerError(f"{label}: end marker must follow begin marker")

    code = "".join(lines[begin + 1 : end])
    if not code.strip():
        raise MarkerError(f"{label}: marker region is empty")

    return ExtractedSnippet(code=code, start_line=begin + 2, end_line=end)


def _read_revision(root: Path, revision: str | None, check: bool) -> str:
    if revision:
        return revision

    lock_path = root / "lean" / "source-lock.json"
    if lock_path.exists():
        data = json.loads(lock_path.read_text(encoding="utf-8"))
        locked_revision = data.get("revision")
        if isinstance(locked_revision, str) and locked_revision:
            return locked_revision

    if check:
        raise StaleGeneratedFiles("lean/source-lock.json is missing a revision")

    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _expected_artifacts(root: Path, revision: str) -> dict[Path, str]:
    config_path = root / "lean" / "items.yml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    items = config.get("items")
    if not isinstance(items, dict) or not items:
        raise ValueError("lean/items.yml must contain a non-empty 'items' mapping")

    generated_dir = root / "lean" / "generated"
    artifacts: dict[Path, str] = {}
    metadata: dict[str, dict[str, str | int]] = {}

    for label, item in sorted(items.items()):
        if not isinstance(item, dict):
            raise ValueError(f"{label}: item configuration must be a mapping")
        source_value = item.get("source")
        repository = item.get("repository")
        if not isinstance(source_value, str) or not isinstance(repository, str):
            raise ValueError(f"{label}: source and repository are required strings")

        source_path = (root / source_value).resolve()
        try:
            source_path.relative_to(root.resolve())
        except ValueError as exc:
            raise ValueError(f"{label}: source must remain inside the project") from exc

        snippet = extract_marked_region(source_path.read_text(encoding="utf-8"), label)
        output_path = generated_dir / f"{label}.lean"
        artifacts[output_path] = snippet.code
        metadata[label] = {
            "language": "lean",
            "snippet": output_path.relative_to(root).as_posix(),
            "source_file": source_value,
            "source_url": (
                f"https://github.com/{repository}/blob/{revision}/{source_value}"
                f"#L{snippet.start_line}-L{snippet.end_line}"
            ),
            "start_line": snippet.start_line,
            "end_line": snippet.end_line,
        }

    artifacts[generated_dir / "items.json"] = json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    artifacts[root / "lean" / "source-lock.json"] = json.dumps(
        {"revision": revision}, indent=2, sort_keys=True
    ) + "\n"
    return artifacts


def synchronize(root: Path, revision: str | None = None, check: bool = False) -> None:
    """Write generated snippets, or fail if check mode finds stale output."""
    root = root.resolve()
    resolved_revision = _read_revision(root, revision, check)
    artifacts = _expected_artifacts(root, resolved_revision)

    if check:
        stale = [
            path.relative_to(root).as_posix()
            for path, expected in artifacts.items()
            if not path.exists() or path.read_text(encoding="utf-8") != expected
        ]
        generated_dir = root / "lean" / "generated"
        expected_paths = set(artifacts)
        if generated_dir.exists():
            stale.extend(
                path.relative_to(root).as_posix()
                for path in generated_dir.glob("*.lean")
                if path not in expected_paths
            )
        if stale:
            raise StaleGeneratedFiles("stale generated files: " + ", ".join(sorted(stale)))
        return

    for path, content in artifacts.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--revision", help="Commit SHA used for source permalinks")
    parser.add_argument("--check", action="store_true", help="Fail instead of writing stale output")
    args = parser.parse_args(argv)

    try:
        synchronize(args.root, revision=args.revision, check=args.check)
    except (MarkerError, StaleGeneratedFiles, ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
