import subprocess
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
MIGRATED_ITEMS = {
    "def-relation": ("foundations/relations.html", "definition"),
    "exm-basic-relations": ("foundations/relations.html", "example"),
    "exr-equal-canonical-relations": ("foundations/relations.html", "exercise"),
    "exr-product-relation-subset": ("foundations/relations.html", "exercise"),
    "exr-de-morgan-union": ("analysis/set-identities.html", "exercise"),
    "exr-double-negation": ("linear-algebra/vector-spaces.html", "exercise"),
    "exr-finite-convex-combinations": (
        "convex-optimization/convex-sets.html",
        "exercise",
    ),
    "exr-parallel-hyperplanes-distance": (
        "convex-optimization/convex-sets.html",
        "exercise",
    ),
    "exr-voronoi-halfspace": ("convex-optimization/convex-sets.html", "exercise"),
}
QMD_PAGES = (
    ROOT / "foundations" / "relations.qmd",
    ROOT / "analysis" / "set-identities.qmd",
    ROOT / "linear-algebra" / "vector-spaces.qmd",
    ROOT / "convex-optimization" / "convex-sets.qmd",
)


def rendered_page(page: str) -> BeautifulSoup:
    return BeautifulSoup((ROOT / "_site" / page).read_text(encoding="utf-8"), "html.parser")


@pytest.fixture(scope="module", autouse=True)
def render_site():
    subprocess.run(["quarto", "render"], cwd=ROOT, check=True)


@pytest.mark.parametrize(
    ("label", "page", "environment"),
    [(label, *details) for label, details in MIGRATED_ITEMS.items()],
)
def test_migrated_item_uses_simple_native_environment(
    label: str, page: str, environment: str
):
    item = rendered_page(page).select_one(f"#{label}.theorem.{environment}")

    assert item is not None
    classes = item.get("class") or []
    assert "lean-paired" not in classes
    assert item.select_one(".theorem-title") is not None
    assert item.select_one(".math-notes-tabset") is None
    assert item.select_one("ul.nav-tabs") is None
    assert item.select_one("[data-lean-id]") is None
    assert "Lean 4" not in item.get_text(" ", strip=True)


@pytest.mark.parametrize(
    ("label", "page"),
    [
        (label, page)
        for label, (page, environment) in MIGRATED_ITEMS.items()
        if environment == "exercise"
    ],
)
def test_every_exercise_has_a_separate_closed_solution(label: str, page: str):
    item = rendered_page(page).select_one(f"#{label}.theorem.exercise")

    assert item is not None
    solution = item.select_one(":scope > .callout.callout-tip")
    assert solution is not None
    toggle = solution.select_one(".callout-header")
    assert toggle is not None
    assert toggle.get("aria-expanded") == "false"


def test_site_contains_exactly_the_nine_migrated_items():
    found = set()
    for page in {page for page, _ in MIGRATED_ITEMS.values()}:
        found.update(
            str(item["id"])
            for item in rendered_page(page).select(".theorem[id]")
            if item.get("id")
        )

    assert found == set(MIGRATED_ITEMS)


def test_index_cross_references_every_migrated_item():
    hrefs = {
        link.get("href")
        for link in rendered_page("index.html").select("a.quarto-xref")
    }
    expected = {
        f"{page}#{label}" for label, (page, _) in MIGRATED_ITEMS.items()
    }

    assert expected.issubset(hrefs)


def test_qmd_authoring_uses_plain_theorem_environment_markup():
    for page in QMD_PAGES:
        source = page.read_text(encoding="utf-8")
        assert ".lean-paired" not in source
        assert "lean-id=" not in source
        assert ".panel-tabset" not in source


def test_finite_convex_combination_proof_handles_k_equals_one():
    source = (ROOT / "convex-optimization" / "convex-sets.qmd").read_text(
        encoding="utf-8"
    )

    assert "The case $k=1$ is immediate" in source


def test_hyperplane_distance_proof_establishes_bound_and_attainment():
    source = (ROOT / "convex-optimization" / "convex-sets.qmd").read_text(
        encoding="utf-8"
    )

    assert "$a\\neq0$" in source
    assert "For every $x_1\\in H_1$ and $x_2\\in H_2$" in source
    assert "This lower bound is attained" in source


def test_solution_disclosure_has_an_explicit_blue_header_style():
    stylesheet = (ROOT / "_site" / "styles.css").read_text(encoding="utf-8")

    assert "--notes-solution-bg" in stylesheet
    assert ".callout-tip.callout-style-default > .callout-header" in stylesheet
