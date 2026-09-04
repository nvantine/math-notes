import subprocess
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
PILOT_ITEMS = {
    "def-relation": "foundations/relations.html",
    "exr-de-morgan-union": "analysis/set-identities.html",
    "exr-double-negation": "linear-algebra/vector-spaces.html",
}


@pytest.fixture(scope="module", autouse=True)
def render_site():
    subprocess.run(["quarto", "render"], cwd=ROOT, check=True)


@pytest.mark.parametrize(("label", "page"), PILOT_ITEMS.items())
def test_pilot_item_uses_a_simple_notes_only_layout(label: str, page: str):
    soup = BeautifulSoup(
        (ROOT / "_site" / page).read_text(encoding="utf-8"), "html.parser"
    )

    item = soup.select_one(f"#{label}.theorem")
    assert item is not None
    classes = item.get("class") or []
    assert "lean-paired" not in classes
    assert item.select_one(".theorem-title") is not None
    assert item.select_one(".math-notes-tabset") is None
    assert item.select_one("ul.nav-tabs") is None
    assert item.select_one("[data-lean-id]") is None
    assert "Lean 4" not in item.get_text(" ", strip=True)


@pytest.mark.parametrize(
    ("label", "page", "environment"),
    [
        ("def-relation", "foundations/relations.html", "definition"),
        ("exr-de-morgan-union", "analysis/set-identities.html", "exercise"),
        ("exr-double-negation", "linear-algebra/vector-spaces.html", "exercise"),
    ],
)
def test_pilot_items_keep_their_environment_class(
    label: str, page: str, environment: str
):
    soup = BeautifulSoup(
        (ROOT / "_site" / page).read_text(encoding="utf-8"), "html.parser"
    )

    item = soup.select_one(f"#{label}")

    assert item is not None
    classes = item.get("class")
    assert classes is not None
    assert "theorem" in classes
    assert environment in classes


def test_exercise_solution_is_separate_and_closed_blue_callout():
    soup = BeautifulSoup(
        (ROOT / "_site" / "analysis" / "set-identities.html").read_text(
            encoding="utf-8"
        ),
        "html.parser",
    )
    item = soup.select_one("#exr-de-morgan-union")

    assert item is not None
    solution = item.select_one(".callout.callout-tip")
    assert solution is not None
    assert solution.parent is item
    toggle = solution.select_one(".callout-header")
    assert toggle is not None
    assert toggle.get("aria-expanded") == "false"


def test_index_cross_references_all_three_pilot_items():
    soup = BeautifulSoup(
        (ROOT / "_site" / "index.html").read_text(encoding="utf-8"), "html.parser"
    )
    hrefs = {link.get("href") for link in soup.select("a.quarto-xref")}

    assert "foundations/relations.html#def-relation" in hrefs
    assert "analysis/set-identities.html#exr-de-morgan-union" in hrefs
    assert "linear-algebra/vector-spaces.html#exr-double-negation" in hrefs


def test_qmd_authoring_uses_plain_theorem_environment_markup():
    for page in (
        ROOT / "foundations" / "relations.qmd",
        ROOT / "analysis" / "set-identities.qmd",
        ROOT / "linear-algebra" / "vector-spaces.qmd",
    ):
        source = page.read_text(encoding="utf-8")
        assert ".lean-paired" not in source
        assert "lean-id=" not in source
        assert ".panel-tabset" not in source
