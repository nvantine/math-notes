# Math Notes

A Quarto-generated personal mathematics site with project-wide cross-references for definitions, theorems, exercises, and proofs.

## Pilot scope

The pilot contains three items adapted from [notes-and-exercises](https://github.com/nvantine/notes-and-exercises). It validates the information architecture and toggle workflow before the remaining notes are migrated.

## Authoring items

An item uses a normal Quarto cross-reference label and environment class:

```markdown
::: {#thm-example name="Example theorem" .theorem}
Mathematical statement and proof go here.
:::
```

The site currently keeps the note presentation simple and does not render Lean tabs. The Lean source and synchronization script remain in the repository for a later implementation.

When Lean source changes, preserve exact source links with this two-commit workflow:

1. Commit the source file and `lean/items.yml`.
2. Run `uv run python scripts/sync_lean.py`. With no `--revision`, it pins the current `HEAD` and refuses to generate if the working source differs from that commit.
3. Review and commit the regenerated snippets, metadata, and source lock.

`--check` compares every current marker region and line range with its locked Git revision. The synchronizer ignores local Git replacement objects, rejects unsafe output paths and symlinks, atomically replaces artifacts without modifying shared hard-link targets, and reports obsolete generated snippets.

Security boundary: write mode is intended for a trusted local working tree. It is not a sandbox against another process running as the same operating-system account and concurrently renaming or replacing entries inside the project while synchronization is in progress. Run it only when no untrusted process can mutate the working tree; CI uses read-only `--check` mode.

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
