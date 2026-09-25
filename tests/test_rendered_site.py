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
    ROOT / "analysis" / "continuous-nowhere-differentiable.qmd",
)

WEIERSTRASS_ITEMS = {
    "def-continuity-epsilon": "definition",
    "def-continuity-sequential": "definition",
    "def-differentiability": "definition",
    "thm-differentiable-implies-continuous": "theorem",
    "exm-absolute-value-cusp": "example",
    "lem-cosine-lipschitz": "lemma",
    "lem-cosine-oscillation": "lemma",
    "lem-cosine-shift": "lemma",
    "lem-reverse-triangle-three-terms": "lemma",
    "thm-weierstrass-absolute-convergence": "theorem",
    "thm-weierstrass-continuity": "theorem",
    "exr-limsup-zero": "exercise",
    "thm-weierstrass-nowhere-differentiable": "theorem",
}


def rendered_page(page: str) -> BeautifulSoup:
    return BeautifulSoup((ROOT / "_site" / page).read_text(encoding="utf-8"), "html.parser")


@pytest.fixture(scope="module", autouse=True)
def render_site(built_site):
    return built_site


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


def test_site_preserves_all_previously_migrated_items():
    found = set()
    for page in {page for page, _ in MIGRATED_ITEMS.values()}:
        found.update(
            str(item["id"])
            for item in rendered_page(page).select(".theorem[id]")
            if item.get("id")
        )

    assert set(MIGRATED_ITEMS).issubset(found)


def test_subject_index_opens_independent_books():
    page = rendered_page("index.html")
    hrefs = {a.get("href") for a in page.select("main a")}
    for subject in ("linear-algebra", "convex-optimization", "analysis", "foundations"):
        assert f"{subject}/index.html" in hrefs
    assert page.select_one("#quarto-sidebar") is None


def test_subject_indexes_cross_reference_their_migrated_items():
    for label, (page, _) in MIGRATED_ITEMS.items():
        subject, chapter = page.split("/")
        hrefs = {
            str(link.get("href")).removeprefix("./")
            for link in rendered_page(f"{subject}/index.html").select("a.quarto-xref")
        }
        assert f"{chapter}#{label}" in hrefs


@pytest.mark.parametrize("subject", ["linear-algebra", "convex-optimization", "analysis", "foundations"])
def test_books_have_independent_navigation_and_search(subject):
    import json

    page = rendered_page(f"{subject}/index.html")
    sidebar = page.select_one("#quarto-sidebar")
    assert sidebar is not None
    assert page.select_one('a[href="../index.html"]') is not None
    assert not any("../" in str(a.get("href", "")) for a in sidebar.select("a.sidebar-link"))
    entries = json.loads((ROOT / "_site" / subject / "search.json").read_text())
    assert entries
    assert all(not entry["href"].startswith("../") for entry in entries)


@pytest.mark.parametrize(("page", "label"), [
    ("linear-algebra/vector-spaces.html", "thm-unique-additive-inverse"),
    ("linear-algebra/vector-spaces.html", "thm-zero-times-vector"),
    ("analysis/continuous-nowhere-differentiable.html", "thm-weierstrass-continuity"),
])
def test_theorem_proofs_are_closed_disclosures(page, label):
    item = rendered_page(page).select_one(f"#{label}")
    proof = item.select_one(":scope > .callout-tip")
    if proof is None:
        proof = item.find_next_sibling("div", class_="callout-tip")
    assert proof is not None
    assert proof.select_one(".callout-header")["aria-expanded"] == "false"
    assert "Proof" in proof.select_one(".callout-title-container").get_text()


def test_internal_links_assets_and_fragments_resolve():
    from urllib.parse import unquote, urlsplit

    site = ROOT / "_site"
    errors = []
    pages = {p: BeautifulSoup(p.read_text(), "html.parser") for p in site.rglob("*.html")
             if "site_libs" not in p.parts and "lean" not in p.parts}
    for path, page in pages.items():
        assert not page.select("a.quarto-xref-unresolved"), path
        for node in page.select("a[href], link[href], script[src], img[src]"):
            href = str(node.get("href", node.get("src", "")))
            url = urlsplit(href)
            if url.scheme or url.netloc or not href:
                continue
            target = (path.parent / unquote(url.path)).resolve() if url.path else path.resolve()
            if target.is_dir():
                target = target / "index.html"
            if not target.is_file():
                errors.append(f"{path.relative_to(site)} -> {href}")
            elif node.name == "a" and url.fragment and target.suffix == ".html":
                target_page = pages.get(target) or BeautifulSoup(target.read_text(), "html.parser")
                if target_page.find(id=unquote(url.fragment)) is None:
                    errors.append(f"{path.relative_to(site)} -> missing #{url.fragment} in {target.name}")
    assert not errors, "\n".join(errors)


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


def test_cross_reference_previews_lazy_load_and_typeset_math():
    page = rendered_page("index.html")
    script = page.select_one("script#xref-math-previews")

    assert script is not None
    source = script.get_text()
    assert "MutationObserver" in source
    assert "typesetPromise" in source
    assert "mathjax@4.0.0/tex-chtml.js" in source
    assert ".tippy-content" in source
    assert "mathJaxPromise = undefined" in source
    assert "const pendingPreviews = new WeakSet()" in source
    assert "const previews = new Set()" in source


def test_weierstrass_paper_is_an_analysis_chapter():
    page = rendered_page("analysis/continuous-nowhere-differentiable.html")
    title = page.select_one("main.content h1.title")

    assert title is not None
    assert "Continuous Everywhere, Nowhere Differentiable" in title.get_text(" ")
    metadata = page.select_one(".quarto-title-meta")
    assert metadata is not None
    assert "Spring 2025" in metadata.get_text(" ", strip=True)
    assert page.select_one("#introduction") is not None
    assert page.select_one("#background") is not None
    assert page.select_one("#construction") is not None
    assert page.select_one("#continuity") is not None
    assert page.select_one("#nowhere-differentiability") is not None

    sidebar_hrefs = {
        link.get("href") for link in page.select("#quarto-sidebar a.sidebar-link")
    }
    assert "./continuous-nowhere-differentiable.html" in sidebar_hrefs


@pytest.mark.parametrize(("label", "environment"), WEIERSTRASS_ITEMS.items())
def test_weierstrass_paper_preserves_mathematical_environments(
    label: str, environment: str
):
    page = rendered_page("analysis/continuous-nowhere-differentiable.html")

    assert page.select_one(f"#{label}.theorem.{environment}") is not None


def test_weierstrass_exercise_has_a_closed_solution():
    page = rendered_page("analysis/continuous-nowhere-differentiable.html")
    exercise = page.select_one("#exr-limsup-zero.exercise")

    assert exercise is not None
    solution = exercise.select_one(":scope > .callout.callout-tip")
    assert solution is not None
    toggle = solution.select_one(".callout-header")
    assert toggle is not None
    assert toggle.get("aria-expanded") == "false"


def test_weierstrass_page_resolves_its_sources():
    page = rendered_page("analysis/continuous-nowhere-differentiable.html")
    cited = {
        key
        for citation in page.select("[data-cites]")
        for key in str(citation.attrs.get("data-cites", "")).split()
    }

    assert {
        "Abbott2015",
        "ClassNotes",
        "SteinShakarchi2003",
        "MITRealAnalysisLecture18",
        "wiki-Karl-Weierstrass",
        "wiki-Weierstrass-function",
    }.issubset(cited)


def test_weierstrass_authoring_uses_mathjax_supported_notation():
    source = (ROOT / "analysis" / "continuous-nowhere-differentiable.qmd").read_text(
        encoding="utf-8"
    )

    assert "\\R" not in source
    assert "\\eps" not in source
    assert "\\begin{equation}" not in source
    assert "\\newpage" not in source


def test_weierstrass_page_preserves_the_sequential_continuity_argument():
    source = (ROOT / "analysis" / "continuous-nowhere-differentiable.qmd").read_text(
        encoding="utf-8"
    )

    assert "Sequential proof" in source
    assert "split the series into a finite head and a uniformly small tail" in source
