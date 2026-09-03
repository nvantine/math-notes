import json
from pathlib import Path

import pytest

from scripts.sync_lean import MarkerError, StaleGeneratedFiles, extract_marked_region, synchronize


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

    synchronize(tmp_path, revision="abc123", check=False)

    assert (tmp_path / "lean" / "generated" / "thm-demo.lean").read_text(encoding="utf-8") == (
        "theorem demo : True := by trivial\n"
    )
    metadata = json.loads((tmp_path / "lean" / "generated" / "items.json").read_text(encoding="utf-8"))
    assert metadata["thm-demo"]["source_url"] == (
        "https://github.com/example/math-notes/blob/abc123/lean/source/Pilot.lean#L2-L2"
    )
    assert metadata["thm-demo"]["snippet"] == "lean/generated/thm-demo.lean"
    lock = json.loads((tmp_path / "lean" / "source-lock.json").read_text(encoding="utf-8"))
    assert lock == {"revision": "abc123"}


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
    (tmp_path / "lean" / "source-lock.json").write_text('{"revision":"abc123"}\n', encoding="utf-8")
    (generated_dir / "thm-demo.lean").write_text("stale\n", encoding="utf-8")

    with pytest.raises(StaleGeneratedFiles, match="thm-demo.lean"):
        synchronize(tmp_path, revision=None, check=True)
