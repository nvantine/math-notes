# Math Notes

A Quarto-generated personal mathematics site with project-wide cross-references and an optional Notes / Lean 4 view for formalized items.

## Pilot scope

The pilot contains three items adapted from [notes-and-exercises](https://github.com/nvantine/notes-and-exercises). It validates the information architecture and toggle workflow before the remaining notes are migrated.

## Local development

```bash
uv sync
uv run pytest
uv run python scripts/sync_lean.py --check
quarto preview
```

The generated site is published at <https://nvantine.github.io/math-notes/>.

See [ROADMAP.md](ROADMAP.md) for deferred work, including a possible browser-based Lean editor.
