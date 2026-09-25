"""Fidelity checks for the LaTeX display-only Lean import (no compiler)."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "lean/latex/main.tex"
SCRIPT = ROOT / "scripts/import_latex_lean.py"
REVISION = "769ae44ffa5a640f43c699548cbdd87ddc63f998"


def test_import_preserves_all_three_leanboxes_byte_for_byte(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--source", str(SOURCE), "--output", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    metadata = json.loads((tmp_path / "items.json").read_text())
    assert (tmp_path / "items.json").read_bytes() == (ROOT / "lean/latex/items.json").read_bytes()
    for item in metadata["items"]:
        for field in ("lean_file", "html_file"):
            assert (tmp_path / item[field]).read_bytes() == (ROOT / "lean/latex" / item[field]).read_bytes()
    source = SOURCE.read_text(encoding="utf-8")
    assert metadata["source_revision"] == REVISION
    assert metadata["source_sha256"] == hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    boxes = re.findall(r"\\begin\{leanbox\}(.*?)\\end\{leanbox\}", source, re.S)
    assert len(boxes) == len(metadata["items"]) == 3
    for box, item in zip(boxes, metadata["items"], strict=True):
        code = re.search(r"\\begin\{minted\}\{lean4\}\n(.*?)\\end\{minted\}", box, re.S)[1]
        url = re.search(r"\\href\{([^}]+)\}", box)[1]
        actual = (tmp_path / item["lean_file"]).read_bytes()
        assert actual == code.encode("utf-8")
        assert item["sha256"] == hashlib.sha256(actual).hexdigest()
        assert item["playground_url"] == url
        start, end = item["source_lines"]
        assert "".join(source.splitlines(keepends=True)[start - 1:end]) == code
        html = BeautifulSoup((tmp_path / item["html_file"]).read_text(), "html.parser")
        assert html.select_one("pre.lean4 code").get_text() == code
        assert html.select_one("pre.lean4 code span") is not None
        assert html.select_one("a")["href"] == url
        assert html.select_one("iframe, script, textarea") is None


def test_import_does_not_modify_symlink_or_hardlink_targets(tmp_path):
    import os

    protected = tmp_path / "protected.txt"
    protected.write_text("keep me")
    output = tmp_path / "output"
    output.mkdir()
    target = output / "zero_smul_eq_zero.lean"
    target.symlink_to(protected)
    result = subprocess.run([sys.executable, str(SCRIPT), "--output", str(output)], capture_output=True)
    assert result.returncode != 0
    assert protected.read_text() == "keep me"
    target.unlink()
    os.link(protected, target)
    result = subprocess.run([sys.executable, str(SCRIPT), "--output", str(output)], capture_output=True)
    assert result.returncode == 0, result.stderr
    assert protected.read_text() == "keep me"
    assert target.stat().st_ino != protected.stat().st_ino


def test_import_rejects_symlinked_output_directory(tmp_path):
    protected = tmp_path / "protected"
    protected.mkdir()
    output = tmp_path / "output"
    output.symlink_to(protected, target_is_directory=True)
    result = subprocess.run([sys.executable, str(SCRIPT), "--output", str(output)], capture_output=True)
    assert result.returncode != 0
    assert not list(protected.iterdir())


def test_rejects_changed_source_instead_of_claiming_pinned_revision(tmp_path):
    changed = tmp_path / "changed.tex"
    changed.write_bytes(SOURCE.read_bytes() + b"\n% changed\n")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--source", str(changed), "--output", str(tmp_path / "out")],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "pinned source" in result.stderr
    assert not (tmp_path / "out/items.json").exists()


def test_subject_chapters_include_source_items_and_sibling_lean_disclosures():
    la = (ROOT / "linear-algebra/vector-spaces.qmd").read_text()
    for anchor in (
        "def-addition", "def-scalar-multiplication", "def-vector-space",
        "thm-unique-additive-inverse", "thm-zero-times-vector", "exr-add-inv-swap",
    ):
        assert f"#{anchor} " in la
    assert "a(bv)=(ab)v" in la
    assert "take $w=(-1)v$" in la
    assert "not a formal proof of the weaker axiom system" in la
    metadata = json.loads((ROOT / "lean/latex/items.json").read_text())
    for item in metadata["items"]:
        assert f'::: {{#{item["lean_id"]} .callout-note collapse="true"}}\n## Lean' in la
        assert f'{{{{< include lean/latex/{item["html_file"]} >}}}}' in la
    cvx = (ROOT / "convex-optimization/convex-sets.qmd").read_text()
    for anchor in ("def-convex-set", "def-hyperplane", "def-halfspace"):
        assert f"#{anchor} " in cvx
    assert "../linear-algebra/vector-spaces.html#def-vector-space" in cvx
    assert "The case $k=1$ is immediate" in cvx
    assert "This lower bound is attained" in cvx
    assert ".callout-note" not in cvx
    foundations = (ROOT / "foundations/relations.qmd").read_text()
    assert "#def-equivalence-relation " in foundations


def test_rendered_lean_is_exact_and_sibling_of_proof_or_solution(tmp_path):
    import shutil

    shutil.copytree(ROOT / "lean/latex", tmp_path / "lean/latex")
    shutil.copy(ROOT / "references.bib", tmp_path / "references.bib")
    for subject, page in (
        ("linear-algebra", "vector-spaces"),
        ("convex-optimization", "convex-sets"),
        ("foundations", "relations"),
    ):
        shutil.copy(ROOT / subject / f"{page}.qmd", tmp_path / f"{page}.qmd")
    (tmp_path / "_quarto.yml").write_text(
        'project:\n  type: book\nbook:\n  title: Import QA\n  chapters:\n'
        '    - index.qmd\n    - vector-spaces.qmd\n    - convex-sets.qmd\n'
        '    - relations.qmd\nbibliography: references.bib\nformat: html\n'
    )
    (tmp_path / "index.qmd").write_text('# Import QA\n')
    result = subprocess.run(["quarto", "render"], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Unable to resolve crossref" not in result.stderr
    page = BeautifulSoup((tmp_path / "_book/vector-spaces.html").read_text(), "html.parser")
    metadata = json.loads((ROOT / "lean/latex/items.json").read_text())
    for item in metadata["items"]:
        math = page.select_one(f'#{item["math_id"]}.theorem')
        assert math is not None
        lean = math.select_one(f':scope > #{item["lean_id"]}.callout-note')
        assert lean is not None
        assert lean.select_one('.callout-header')["aria-expanded"] == "false"
        title = lean.select_one('.callout-title-container')
        assert title is not None
        for sr_only in title.select('.screen-reader-only'):
            sr_only.decompose()
        assert title.get_text(strip=True) == "Lean"
        assert lean.select_one("pre.lean4 code").get_text() == (ROOT / "lean/latex" / item["lean_file"]).read_text()
        assert lean.select_one("pre span") is not None
        assert lean.select_one('a[href^="https://live.lean-lang.org/"]')["href"] == item["playground_url"]
        assert lean.select_one(".proof, .callout-tip") is None
        sibling = math.select_one(":scope > .proof, :scope > .callout-tip")
        assert sibling is not None
        if item["math_id"].startswith("exr-"):
            assert sibling.select_one('.callout-header')["aria-expanded"] == "false"
    for name, anchors in {
        "convex-sets": ["def-convex-set", "def-hyperplane", "def-halfspace"],
        "relations": ["def-equivalence-relation"],
    }.items():
        soup = BeautifulSoup((tmp_path / f"_book/{name}.html").read_text(), "html.parser")
        for anchor in anchors:
            assert soup.select_one(f"#{anchor}.theorem.definition") is not None
