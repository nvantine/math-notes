from pathlib import Path
import subprocess

from bs4 import BeautifulSoup
import pytest


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
def test_pilot_item_uses_native_notes_and_lean_tabs(label: str, page: str):
    soup = BeautifulSoup((ROOT / "_site" / page).read_text(encoding="utf-8"), "html.parser")

    item = soup.select_one(f"#{label}.theorem.lean-paired")
    assert item is not None
    tabs = item.select("ul.nav-tabs .nav-link")
    assert [tab.get_text(" ", strip=True) for tab in tabs] == ["Notes", "Lean 4"]
    assert tabs[0].get("aria-selected") == "true"
    assert tabs[1].get("aria-selected") == "false"

    panels = item.select("div.tab-content > div.tab-pane")
    assert len(panels) == 2
    assert {"show", "active"}.issubset(panels[0].get("class", []))
    assert "active" not in panels[1].get("class", [])
    assert panels[1].select_one("pre.sourceCode.lean > code") is not None
    source_link = panels[1].select_one("a.lean-source-link")
    assert source_link is not None
    assert "/blob/b9dc146062b71e905e550bcf9f06c8ab5caaf9e3/lean/source/Pilot.lean#L" in source_link["href"]


def test_index_cross_references_all_three_pilot_items():
    soup = BeautifulSoup((ROOT / "_site" / "index.html").read_text(encoding="utf-8"), "html.parser")
    hrefs = {link.get("href") for link in soup.select("a.quarto-xref")}

    assert "foundations/relations.html#def-relation" in hrefs
    assert "analysis/set-identities.html#exr-de-morgan-union" in hrefs
    assert "linear-algebra/vector-spaces.html#exr-double-negation" in hrefs


def test_qmd_authoring_does_not_repeat_tabset_markup():
    for page in (
        ROOT / "foundations" / "relations.qmd",
        ROOT / "analysis" / "set-identities.qmd",
        ROOT / "linear-algebra" / "vector-spaces.qmd",
    ):
        source = page.read_text(encoding="utf-8")
        assert ".lean-paired" in source
        assert "lean-id=" in source
        assert ".panel-tabset" not in source
