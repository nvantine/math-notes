# Math Notes

A Quarto-generated personal mathematics site with project-wide cross-references and an optional Notes / Lean 4 view for formalized items.

## Pilot scope

The pilot contains three items adapted from [notes-and-exercises](https://github.com/nvantine/notes-and-exercises). It validates the information architecture and toggle workflow before the remaining notes are migrated.

## Authoring paired items

A paired item needs only the normal Quarto cross-reference label plus two attributes:

```markdown
::: {#thm-example name="Example theorem" .lean-paired lean-id="thm-example"}
The mathematical statement and proof go here.
:::
```

The Lua extension creates accessible Bootstrap tabs using Quarto's bundled runtime—there is no site-specific JavaScript to maintain. `scripts/sync_lean.py` extracts the matching marker-delimited region from `lean/source/Pilot.lean`, generates the displayed snippet, and creates a commit-pinned GitHub source link.

The pilot Lean snippets are display examples and are not yet compiled in CI because this repository is not a Lean/Lake project. A standalone formalization repository and browser editor remain future work.

## Local development

```bash
uv sync
uv run pytest
uv run python scripts/sync_lean.py --check
quarto preview
```

The generated site is published at <https://nvantine.github.io/math-notes/>.

See [ROADMAP.md](ROADMAP.md) for deferred work, including a possible browser-based Lean editor.
