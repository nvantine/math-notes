# Mathematical notes

A small subject index opens independent Quarto books, each with its own contents,
search, numbering, and references. Published at <https://nvantine.github.io/math-notes/>.

- `linear-algebra/`: vector-space axioms, first theorems, and worked exercises.
- `convex-optimization/`: convex sets, hyperplanes, halfspaces, and worked exercises.
- `analysis/`: set identities and the Weierstrass-function paper.
- `foundations/`: relations and equivalence relations.

## Source and scope

The books primarily adapt [notes-and-exercises](https://github.com/nvantine/notes-and-exercises),
pinned to revision `769ae44ffa5a640f43c699548cbdd87ddc63f998`. Additions are modest:
hyperplane/halfspace definitions, short connective exposition, and cross-references.
Mathematical corrections are identified in the chapter and recorded in
[the migration notes](docs/source-migration.md). Empty source sections are not
turned into empty chapters. The existing analysis paper remains available.

The three displayed Lean snippets and their original playground URLs are preserved
exactly from the LaTeX. They are display-only excerpts, not locally compiler-checked
proofs. There is no embedded editor, Lean installation, or new formalization.

## Build and preview

Requires Quarto 1.10.18 and uv (Python 3.11+). From the repository root:

```sh
uv sync --locked
uv run python scripts/build_site.py
uv run python -m http.server 8877 --bind 127.0.0.1 --directory _site
```

Open `http://127.0.0.1:8877`. Re-run the build after editing; the HTTP server serves
the new output. `quarto render` alone renders only the subject index, not the books.

The builder stages each subject as a separate Quarto project under ignored
`.build/`, supplying `_shared.yml`, styles, bibliography, disclosure helpers, and
Lean includes. It renders the home page and books before replacing `_site/`.
Existing chapter URLs and mathematical anchor IDs are retained. Generated staging
files are never authoring sources. Edit the subject `.qmd` and `_quarto.yml` files.
Each new chapter must be listed in its subject's `book.chapters` configuration.

## Verification

```sh
uv run playwright install chromium
uv run pytest
uv run python scripts/sync_lean.py --check
```

On Linux CI, install browser system dependencies with
`uv run playwright install --with-deps chromium`. Tests build the entire site and
check original items, all local links/anchors/assets, source/snippet fidelity,
independent navigation/search, closed disclosures, keyboard operation, Lean deep
links, math previews, and mobile/desktop layouts in light/dark themes. Browser
math tests require access to the MathJax CDN, as does the normal site.

The publish workflow tests the assembled site, then uses Quarto's `--no-render`
publish path so the final publish step does not erase the subject books.

## Authoring and links

Use normal native mathematical environments with stable semantic labels:

```markdown
::: {#thm-example name="Example theorem" .theorem}
The statement remains visible.

::: {.proof}
The proof goes here. The shared filter presents it as a closed Proof disclosure.
:::
:::
```

For exercises, keep a `.callout-tip collapse="true"` titled `Solution` inside the
exercise. When the source provides Lean, add a separate sibling
`.callout-note collapse="true"` titled `Lean`, with its own `#lean-...` anchor and
include the imported HTML. Do not place Lean inside the proof or solution.
`disclosures.html` supplies keyboard activation and opens a linked disclosure.

Within a book use `@def-vector-space` or `@thm-zero-times-vector`. Across books use
an explicit relative URL such as
`../linear-algebra/vector-spaces.html#def-vector-space`. Link to Lean dependencies
by their own fragment, e.g. `#lean-zero-times-vector`. The local-link tests reject
broken destinations. `xref-math.html` typesets math in delayed Quarto hover previews.

`styles.css` is the shared plain-CSS theme, mirrored in `styles.scss` for continuity
with the previous project. Keep both in sync; no Sass build or external fonts are
required.

## Updating imported Lean

`lean/latex/main.tex` is an archival snapshot, not a second editable source of truth.
`lean/latex/items.json` records its revision/hash, source line ranges, exact code
hashes, and the original encoded playground links. Regenerate the pinned assets:

```sh
uv run python scripts/import_latex_lean.py
uv run pytest tests/test_latex_import.py
```

For a newer LaTeX revision, review and replace the archival snapshot, explicitly
update the importer's revision/hash and item mapping, migrate changed prose, and
update fidelity tests. A changed snapshot is rejected until its pin is updated.
The importer uses the existing no-follow, atomic artifact writer; linked output
files cannot overwrite unrelated files.

The old `lean/source/Pilot.lean`, `lean/generated/`, and marker synchronizer are
retained as an archive and are not shown on the site. Their existing synchronization
checks still run. Do not substitute those old examples for the source Lean blocks.
