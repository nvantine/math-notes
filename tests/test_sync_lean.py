import json
import os
import subprocess
from pathlib import Path

import pytest

from scripts.sync_lean import (
    MarkerError,
    StaleGeneratedFiles,
    extract_marked_region,
    synchronize,
)


def commit_fixture(root: Path) -> str:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=root, check=True
    )
    subprocess.run(
        ["git", "add", "lean/source", "lean/items.yml"], cwd=root, check=True
    )
    subprocess.run(["git", "commit", "-q", "-m", "source"], cwd=root, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_extract_marked_region_returns_code_and_source_lines():
    source = """import Mathlib

-- MATH_NOTES_BEGIN thm-demo
theorem demo : True := by
  trivial
-- MATH_NOTES_END thm-demo
"""

    snippet = extract_marked_region(source, "thm-demo")

    assert snippet.code == "theorem demo : True := by\n  trivial\n"
    assert snippet.start_line == 4
    assert snippet.end_line == 5


@pytest.mark.parametrize(
    "source, message",
    [
        ("theorem demo : True := by trivial\n", "missing marker pair"),
        (
            """-- MATH_NOTES_BEGIN thm-demo
one
-- MATH_NOTES_END thm-demo
-- MATH_NOTES_BEGIN thm-demo
two
-- MATH_NOTES_END thm-demo
""",
            "exactly one marker pair",
        ),
    ],
)
def test_extract_marked_region_rejects_missing_or_duplicate_markers(source, message):
    with pytest.raises(MarkerError, match=message):
        extract_marked_region(source, "thm-demo")


def test_synchronize_writes_snippet_metadata_and_commit_pinned_link(tmp_path: Path):
    source_dir = tmp_path / "lean" / "source"
    source_dir.mkdir(parents=True)
    (source_dir / "Pilot.lean").write_text(
        """-- MATH_NOTES_BEGIN thm-demo
theorem demo : True := by trivial
-- MATH_NOTES_END thm-demo
""",
        encoding="utf-8",
    )
    (tmp_path / "lean" / "items.yml").write_text(
        """items:
  thm-demo:
    source: lean/source/Pilot.lean
    repository: example/math-notes
""",
        encoding="utf-8",
    )

    revision = commit_fixture(tmp_path)
    synchronize(tmp_path, revision=revision, check=False)

    assert (tmp_path / "lean" / "generated" / "thm-demo.lean").read_text(
        encoding="utf-8"
    ) == ("theorem demo : True := by trivial\n")
    assert "<span" in (
        tmp_path / "lean" / "generated" / "thm-demo.html"
    ).read_text(encoding="utf-8")
    metadata = json.loads(
        (tmp_path / "lean" / "generated" / "items.json").read_text(encoding="utf-8")
    )
    assert metadata["thm-demo"]["source_url"] == (
        f"https://github.com/example/math-notes/blob/{revision}/lean/source/Pilot.lean#L2-L2"
    )
    assert metadata["thm-demo"]["snippet"] == "lean/generated/thm-demo.lean"
    assert metadata["thm-demo"]["highlighted_snippet"] == (
        "lean/generated/thm-demo.html"
    )
    lock = json.loads(
        (tmp_path / "lean" / "source-lock.json").read_text(encoding="utf-8")
    )
    assert lock == {"revision": revision}


def test_check_mode_detects_stale_generated_files(tmp_path: Path):
    source_dir = tmp_path / "lean" / "source"
    generated_dir = tmp_path / "lean" / "generated"
    source_dir.mkdir(parents=True)
    generated_dir.mkdir(parents=True)
    (source_dir / "Pilot.lean").write_text(
        """-- MATH_NOTES_BEGIN thm-demo
theorem demo : True := by trivial
-- MATH_NOTES_END thm-demo
""",
        encoding="utf-8",
    )
    (tmp_path / "lean" / "items.yml").write_text(
        """items:
  thm-demo:
    source: lean/source/Pilot.lean
    repository: example/math-notes
""",
        encoding="utf-8",
    )
    revision = commit_fixture(tmp_path)
    (tmp_path / "lean" / "source-lock.json").write_text(
        json.dumps({"revision": revision}) + "\n", encoding="utf-8"
    )
    (generated_dir / "thm-demo.lean").write_text("stale\n", encoding="utf-8")

    with pytest.raises(StaleGeneratedFiles, match="thm-demo.lean"):
        synchronize(tmp_path, revision=None, check=True)


def test_synchronize_rejects_label_path_traversal(tmp_path: Path):
    source_dir = tmp_path / "lean" / "source"
    source_dir.mkdir(parents=True)
    label = "../../../escaped"
    (source_dir / "Pilot.lean").write_text(
        f"-- MATH_NOTES_BEGIN {label}\ntheorem escaped : True := by trivial\n"
        f"-- MATH_NOTES_END {label}\n",
        encoding="utf-8",
    )
    (tmp_path / "lean" / "items.yml").write_text(
        f'''items:
  "{label}":
    source: lean/source/Pilot.lean
    repository: example/math-notes
''',
        encoding="utf-8",
    )

    revision = commit_fixture(tmp_path)
    with pytest.raises(ValueError, match="lowercase kebab-case"):
        synchronize(tmp_path, revision=revision, check=False)

    assert not (tmp_path.parent / "escaped.lean").exists()


def test_synchronize_rejects_symlink_generated_output(tmp_path: Path):
    source_dir = tmp_path / "lean" / "source"
    generated_dir = tmp_path / "lean" / "generated"
    source_dir.mkdir(parents=True)
    generated_dir.mkdir(parents=True)
    (source_dir / "Pilot.lean").write_text(
        """-- MATH_NOTES_BEGIN thm-demo
theorem demo : True := by trivial
-- MATH_NOTES_END thm-demo
""",
        encoding="utf-8",
    )
    (tmp_path / "lean" / "items.yml").write_text(
        """items:
  thm-demo:
    source: lean/source/Pilot.lean
    repository: example/math-notes
""",
        encoding="utf-8",
    )
    revision = commit_fixture(tmp_path)
    outside = tmp_path / "outside.lean"
    outside.write_text("do not overwrite\n", encoding="utf-8")
    (generated_dir / "thm-demo.lean").symlink_to(outside)

    with pytest.raises(ValueError, match="symbolic link"):
        synchronize(tmp_path, revision=revision, check=False)

    assert outside.read_text(encoding="utf-8") == "do not overwrite\n"


def test_write_mode_rejects_source_that_differs_from_current_commit(tmp_path: Path):
    source_dir = tmp_path / "lean" / "source"
    source_dir.mkdir(parents=True)
    source_path = source_dir / "Pilot.lean"
    source_path.write_text(
        """-- MATH_NOTES_BEGIN thm-demo
theorem demo : True := by trivial
-- MATH_NOTES_END thm-demo
""",
        encoding="utf-8",
    )
    (tmp_path / "lean" / "items.yml").write_text(
        """items:
  thm-demo:
    source: lean/source/Pilot.lean
    repository: example/math-notes
""",
        encoding="utf-8",
    )
    revision = commit_fixture(tmp_path)
    synchronize(tmp_path, revision=revision, check=False)
    source_path.write_text(
        """-- MATH_NOTES_BEGIN thm-demo
theorem changed : True := by trivial
-- MATH_NOTES_END thm-demo
""",
        encoding="utf-8",
    )

    with pytest.raises(StaleGeneratedFiles, match="does not match revision"):
        synchronize(tmp_path, revision=None, check=False)


def test_write_mode_removes_obsolete_generated_snippets(tmp_path: Path):
    source_dir = tmp_path / "lean" / "source"
    generated_dir = tmp_path / "lean" / "generated"
    source_dir.mkdir(parents=True)
    generated_dir.mkdir(parents=True)
    (source_dir / "Pilot.lean").write_text(
        """-- MATH_NOTES_BEGIN thm-demo
theorem demo : True := by trivial
-- MATH_NOTES_END thm-demo
""",
        encoding="utf-8",
    )
    (tmp_path / "lean" / "items.yml").write_text(
        """items:
  thm-demo:
    source: lean/source/Pilot.lean
    repository: example/math-notes
""",
        encoding="utf-8",
    )
    revision = commit_fixture(tmp_path)
    obsolete = generated_dir / "old-item.lean"
    obsolete.write_text("obsolete\n", encoding="utf-8")

    synchronize(tmp_path, revision=revision, check=False)

    assert not obsolete.exists()


def test_write_mode_replaces_hardlinked_output_without_touching_other_link(
    tmp_path: Path,
):
    source_dir = tmp_path / "lean" / "source"
    generated_dir = tmp_path / "lean" / "generated"
    source_dir.mkdir(parents=True)
    generated_dir.mkdir(parents=True)
    (source_dir / "Pilot.lean").write_text(
        """-- MATH_NOTES_BEGIN thm-demo
theorem demo : True := by trivial
-- MATH_NOTES_END thm-demo
""",
        encoding="utf-8",
    )
    (tmp_path / "lean" / "items.yml").write_text(
        """items:
  thm-demo:
    source: lean/source/Pilot.lean
    repository: example/math-notes
""",
        encoding="utf-8",
    )
    revision = commit_fixture(tmp_path)
    outside = tmp_path / "outside.lean"
    outside.write_text("do not overwrite\n", encoding="utf-8")
    output = generated_dir / "thm-demo.lean"
    os.link(outside, output)

    synchronize(tmp_path, revision=revision, check=False)

    assert outside.read_text(encoding="utf-8") == "do not overwrite\n"
    assert output.read_text(encoding="utf-8") == "theorem demo : True := by trivial\n"
    assert outside.stat().st_ino != output.stat().st_ino


def test_revision_verification_ignores_local_git_replacement_objects(tmp_path: Path):
    source_dir = tmp_path / "lean" / "source"
    source_dir.mkdir(parents=True)
    source_path = source_dir / "Pilot.lean"
    source_path.write_text(
        """-- MATH_NOTES_BEGIN thm-demo
theorem original : True := by trivial
-- MATH_NOTES_END thm-demo
""",
        encoding="utf-8",
    )
    (tmp_path / "lean" / "items.yml").write_text(
        """items:
  thm-demo:
    source: lean/source/Pilot.lean
    repository: example/math-notes
""",
        encoding="utf-8",
    )
    original_revision = commit_fixture(tmp_path)
    source_path.write_text(
        """-- MATH_NOTES_BEGIN thm-demo
theorem replacement : True := by trivial
-- MATH_NOTES_END thm-demo
""",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "lean/source/Pilot.lean"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "replacement"], cwd=tmp_path, check=True
    )
    replacement_revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "replace", original_revision, replacement_revision],
        cwd=tmp_path,
        check=True,
    )

    with pytest.raises(StaleGeneratedFiles, match="does not match revision"):
        synchronize(tmp_path, revision=original_revision, check=False)
