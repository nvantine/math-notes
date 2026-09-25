# LaTeX source migration

## Provenance and scope

Source: [`nvantine/notes-and-exercises`, `main.tex` at `769ae44ffa5a640f43c699548cbdd87ddc63f998`](https://github.com/nvantine/notes-and-exercises/blob/769ae44ffa5a640f43c699548cbdd87ddc63f998/main.tex).

The complete source was read, including the exercises, solutions, and all three Lean boxes. A byte-for-byte snapshot is retained at `lean/latex/main.tex`; its SHA-256 is `35bd2200db814a7636a101045c7a93bf17ec4fb60e1ea73fd7c4351b2dc771f9`. This is an archival input, not a document included in the public chapters.

The update focuses on populated Foundations, Linear Algebra, and Convex Optimization content. Empty Subspaces, Finite-Dimensional Vector Spaces (including an empty definition), and Real Analysis placeholders are not invented into chapters. The populated Advanced Calculus exercise was already migrated to `analysis/set-identities.qmd`; analysis files were not modified in this migration.

Programmatic inventory of populated source environments:

| Source chapter | Definitions | Examples | Theorems | Exercises |
| --- | ---: | ---: | ---: | ---: |
| Foundations | 2 | 1 | 0 | 2 |
| Linear Algebra | 3 | 0 | 2 | 2 |
| Advanced Calculus | 0 | 0 | 0 | 1 |
| Convex Optimization | 1 | 0 | 0 | 3 |

The one empty Linear Algebra definition is excluded. There are also three `leanbox` environments, and a separate shared-context `minted` block. The shared context is recorded in the metadata, not duplicated into each exact snippet.

## Native labels

Labels within each subject book use Quarto cross-references (`@def-vector-space`, etc.). Cross-subject links use explicit relative HTML URLs: the convex chapter links to `../linear-algebra/vector-spaces.html#def-vector-space`.

| Source item | Quarto label |
| --- | --- |
| Relation | `def-relation` |
| Basic relations | `exm-basic-relations` |
| Equality of empty, discrete, diagonal relations | `exr-equal-canonical-relations` |
| Product of relations | `exr-product-relation-subset` |
| Equivalence relation | `def-equivalence-relation` |
| Addition | `def-addition` |
| Scalar multiplication | `def-scalar-multiplication` |
| Vector space | `def-vector-space` |
| Unique additive inverse | `thm-unique-additive-inverse` |
| Zero times a vector | `thm-zero-times-vector` |
| Double negation | `exr-double-negation` |
| Replacing additive inverses by the zero-scalar condition | `exr-add-inv-swap` |
| Convex set | `def-convex-set` |
| Finite convex combinations | `exr-finite-convex-combinations` |
| Distance between parallel hyperplanes | `exr-parallel-hyperplanes-distance` |
| Voronoi description of a halfspace | `exr-voronoi-halfspace` |

The modest additional definitions `def-hyperplane` and `def-halfspace` fix the geometric notation used in the source exercises. They are exposition added during migration, not claims of verbatim source content. Brief connective prose and prerequisite cross-links have also been added. Existing Axler and Boyd–Vandenberghe citations are retained.

## Mathematical corrections and retained repairs

- **Vector-space axioms:** the source omitted scalar associativity. Added `a(bv)=(ab)v`, with quantifiers, and aligned the scalar/vector names in the distributive laws. The chapter explicitly identifies this correction.
- **Unique inverse:** existence is supplied by the additive-inverse axiom; the calculation proves uniqueness. The source's closing remark suggested that the uniqueness argument implicitly establishes existence. The migrated remark separates those obligations rather than repeating that claim.
- **Replacement axiom exercise:** the forward implication cites the zero-scalar theorem (the source cited inverse uniqueness). In the reverse implication, construct `w=(-1)v` by scalar multiplication rather than assuming an additive inverse `-v` exists. The chapter explicitly identifies both repairs.
- **`add_inv_swap` Lean context:** the exact source proof assumes `[AddCommGroup V] [Module ℝ V]`, so it already assumes additive inverses. The Lean disclosure explicitly says that this is not a formal proof of the weaker axiom system in the exercise. The code is preserved, not silently repaired.
- **Finite convex combinations:** retain the existing corrected `k=1` case, as well as the `k=2` case and the source's induction argument.
- **Hyperplane distance:** retain the existing explicit `a≠0` assumption and Cauchy–Schwarz lower-bound/attainment proof. The source identified a perpendicular component as the distance without fully establishing the infimum; the retained proof establishes both directions. The resulting formula is unchanged.
- **Foundations:** retain the earlier corrections: the diagonal example is explicitly homogeneous; equality of all three canonical relations is proved in both directions on the common set; the product relation is a subset of `(X₁×X₂)²`, not `X₁×X₂` as written in the source solution.

Presentation-only conversions replace source macros such as `\F` and `\R` with MathJax-compatible `\mathbb{F}` and `\mathbb{R}`, replace LaTeX layout commands with chapter sections, and express environments as native Quarto theorem divs. Solutions remain closed `.callout-tip` disclosures. The theorem proofs use native `.proof` divs in source; the shared `proofs.lua` filter presents them as initially closed Proof disclosures.

## Exact Lean assets and build integration

Run from the repository root:

```sh
.venv/bin/python scripts/import_latex_lean.py
.venv/bin/python -m pytest tests/test_latex_import.py tests/test_sync_lean.py
```

The importer rejects a changed input hash rather than falsely attaching the pinned revision to arbitrary source. It extracts only the code between each Lean box's `minted` delimiters, preserving UTF-8, indentation, comments, and the final newline. It does not add imports or alter tactics. It preserves each original `https://live.lean-lang.org/#codez=...` URL character-for-character, including percent escapes.

| Mathematical parent | Lean disclosure anchor | Include path |
| --- | --- | --- |
| `thm-zero-times-vector` | `lean-zero-times-vector` | `lean/latex/zero_smul_eq_zero.html` |
| `exr-double-negation` | `lean-double-negation` | `lean/latex/double_negation.html` |
| `exr-add-inv-swap` | `lean-add-inv-swap` | `lean/latex/add_inv_swap.html` |

Each include has an adjacent exact `.lean` file. `lean/latex/items.json` records source provenance, line ranges, code SHA-256 values, context, file names, matching mathematical/Lean IDs, and original playground URLs. HTML is escaped by Pygments' `lean4` lexer and contains actual token spans under `pre.lean4 > code` within `.latex-lean-snippet`.

**Book staging requirement:** copy shared `lean/latex/` into each subject staging root alongside the staged chapter `.qmd`, so the include paths above resolve. No compiler, embedded editor, iframe, or local Lean build is involved. Link out to the original playground. The existing canonical pilot under `lean/source`, `lean/generated`, `lean/items.yml`, and `lean/source-lock.json` remains untouched and is not displayed by these chapters.

The new Lean disclosures are `.callout-note collapse="true"`, visibly titled **Lean**, and are direct children of the corresponding theorem/exercise, siblings of Proof/Solution—not nested inside them. Each references its mathematical parent, and `add_inv_swap` links to its zero-scalar Lean dependency. No Lean is invented for convex optimization or foundations.

## Verification

The importer was developed test-first: extraction/fidelity and altered-source rejection were each observed failing before implementation. Tests compare generated and checked-in files, the complete exact snippet text, source line ranges, hashes, and playground URLs against the pinned snapshot. An isolated Quarto book render verifies actual theorem markup, sibling disclosures, closed initial states, visible Lean titles, preserved code text and links, token spans, added definitions, and resolved within-book cross-references. The archived pilot synchronization tests remain green.

The isolated render deliberately does not own final subject-book configuration, CSS colors, cross-book deployment routes, or browser visual QA. Those remain integration checks for the parent build/publish workflow.
