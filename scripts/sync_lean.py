"""Synchronize marker-delimited Lean snippets for the Quarto site."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import subprocess
from dataclasses import dataclass
from pathlib import Path

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
import yaml


class MarkerError(ValueError):
    """Raised when a marker pair is missing or ambiguous."""


class StaleGeneratedFiles(RuntimeError):
    """Raised when check mode finds generated files that need updating."""


LABEL_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")


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


def highlight_lean(code: str) -> str:
    """Return escaped, span-based HTML highlighting for a Lean snippet."""
    return highlight(
        code,
        get_lexer_by_name("lean4"),
        HtmlFormatter(nowrap=True),
    )


def _resolve_git_revision(root: Path, revision: str) -> str:
    result = subprocess.run(
        [
            "git",
            "--no-replace-objects",
            "rev-parse",
            "--verify",
            f"{revision}^{{commit}}",
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _read_revision(root: Path, revision: str | None, check: bool) -> str:
    if revision:
        return _resolve_git_revision(root, revision)

    lock_path = root / "lean" / "source-lock.json"
    if check:
        if lock_path.exists():
            data = json.loads(lock_path.read_text(encoding="utf-8"))
            locked_revision = data.get("revision")
            if isinstance(locked_revision, str) and locked_revision:
                return _resolve_git_revision(root, locked_revision)
        raise StaleGeneratedFiles("lean/source-lock.json is missing a revision")

    return _resolve_git_revision(root, "HEAD")


def _read_file_at_revision(root: Path, revision: str, source_value: str) -> str:
    result = subprocess.run(
        ["git", "--no-replace-objects", "show", f"{revision}:{source_value}"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise StaleGeneratedFiles(
            f"{source_value}: file is unavailable at revision {revision}"
        )
    return result.stdout


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
        if not isinstance(label, str) or not LABEL_PATTERN.fullmatch(label):
            raise ValueError(f"{label!r}: label must be lowercase kebab-case")
        if not isinstance(item, dict):
            raise TypeError(f"{label}: item configuration must be a mapping")
        source_value = item.get("source")
        repository = item.get("repository")
        if not isinstance(source_value, str) or not isinstance(repository, str):
            raise TypeError(f"{label}: source and repository are required strings")

        source_path = (root / source_value).resolve()
        try:
            source_path.relative_to(root.resolve())
        except ValueError as exc:
            raise ValueError(f"{label}: source must remain inside the project") from exc

        snippet = extract_marked_region(source_path.read_text(encoding="utf-8"), label)
        revision_snippet = extract_marked_region(
            _read_file_at_revision(root, revision, source_value), label
        )
        if snippet != revision_snippet:
            raise StaleGeneratedFiles(
                f"{label}: current source does not match revision {revision}"
            )
        output_path = generated_dir / f"{label}.lean"
        highlighted_output_path = generated_dir / f"{label}.html"
        artifacts[output_path] = snippet.code
        artifacts[highlighted_output_path] = highlight_lean(snippet.code)
        metadata[label] = {
            "language": "lean",
            "snippet": output_path.relative_to(root).as_posix(),
            "highlighted_snippet": highlighted_output_path.relative_to(
                root
            ).as_posix(),
            "source_file": source_value,
            "source_url": (
                f"https://github.com/{repository}/blob/{revision}/{source_value}"
                f"#L{snippet.start_line}-L{snippet.end_line}"
            ),
            "start_line": snippet.start_line,
            "end_line": snippet.end_line,
        }

    artifacts[generated_dir / "items.json"] = (
        json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    )
    artifacts[root / "lean" / "source-lock.json"] = (
        json.dumps({"revision": revision}, indent=2, sort_keys=True) + "\n"
    )
    return artifacts


def _validate_output_path(root: Path, path: Path) -> None:
    """Require generated artifacts to stay inside the project without symlinks."""
    cursor = path
    while cursor != root:
        if cursor.is_symlink():
            raise ValueError(f"refusing symbolic link output: {path.relative_to(root)}")
        if cursor.parent == cursor:
            raise ValueError(f"output must remain inside the project: {path}")
        cursor = cursor.parent

    try:
        path.resolve(strict=False).relative_to(root)
    except ValueError as exc:
        raise ValueError(f"output must remain inside the project: {path}") from exc


def _open_directory_beneath(root: Path, directory: Path, *, create: bool) -> int:
    """Open a directory below ``root`` without following path-component symlinks."""
    relative = directory.relative_to(root)
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    current_fd = os.open(root, directory_flags)
    try:
        for part in relative.parts:
            try:
                next_fd = os.open(part, directory_flags, dir_fd=current_fd)
            except FileNotFoundError:
                if not create:
                    raise
                try:
                    os.mkdir(part, mode=0o755, dir_fd=current_fd)
                except FileExistsError:
                    pass
                next_fd = os.open(part, directory_flags, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except BaseException:
        os.close(current_fd)
        raise


def _atomic_write_text(root: Path, path: Path, content: str) -> None:
    """Atomically replace an artifact without following links or shared inodes."""
    _validate_output_path(root, path)
    directory_fd = _open_directory_beneath(root, path.parent, create=True)
    temporary_name = f".{path.name}.tmp-{secrets.token_hex(12)}"
    temporary_exists = False
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        file_fd = os.open(temporary_name, flags, 0o644, dir_fd=directory_fd)
        temporary_exists = True
        with os.fdopen(file_fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(
            temporary_name,
            path.name,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
        )
        temporary_exists = False
        os.fsync(directory_fd)
    finally:
        if temporary_exists:
            try:
                os.unlink(temporary_name, dir_fd=directory_fd)
            except FileNotFoundError:
                pass
        os.close(directory_fd)


def _unlink_output(root: Path, path: Path) -> None:
    """Unlink one validated artifact relative to an opened no-follow directory."""
    _validate_output_path(root, path)
    directory_fd = _open_directory_beneath(root, path.parent, create=False)
    try:
        os.unlink(path.name, dir_fd=directory_fd)
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def synchronize(root: Path, revision: str | None = None, check: bool = False) -> None:
    """Write generated snippets, or fail if check mode finds stale output."""
    root = root.resolve()
    resolved_revision = _read_revision(root, revision, check)
    artifacts = _expected_artifacts(root, resolved_revision)
    for path in artifacts:
        _validate_output_path(root, path)

    generated_dir = root / "lean" / "generated"
    expected_paths = set(artifacts)
    obsolete_paths: list[Path] = []
    if generated_dir.exists():
        for path in generated_dir.iterdir():
            if path.suffix not in {".lean", ".html"}:
                continue
            _validate_output_path(root, path)
            if not path.is_file():
                raise ValueError(
                    f"generated output is not a regular file: {path.relative_to(root)}"
                )
            if path not in expected_paths:
                obsolete_paths.append(path)

    if check:
        stale = [
            path.relative_to(root).as_posix()
            for path, expected in artifacts.items()
            if not path.exists() or path.read_text(encoding="utf-8") != expected
        ]
        stale.extend(path.relative_to(root).as_posix() for path in obsolete_paths)
        if stale:
            raise StaleGeneratedFiles(
                "stale generated files: " + ", ".join(sorted(stale))
            )
        return

    for path in obsolete_paths:
        _unlink_output(root, path)

    for path, content in artifacts.items():
        _atomic_write_text(root, path, content)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--revision", help="Commit SHA used for source permalinks")
    parser.add_argument(
        "--check", action="store_true", help="Fail instead of writing stale output"
    )
    args = parser.parse_args(argv)

    try:
        synchronize(args.root, revision=args.revision, check=args.check)
    except (
        MarkerError,
        StaleGeneratedFiles,
        TypeError,
        ValueError,
        OSError,
        subprocess.CalledProcessError,
    ) as exc:
        parser.exit(1, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
