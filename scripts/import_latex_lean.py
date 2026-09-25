"""Import the pinned LaTeX Lean boxes as exact, display-only UTF-8 assets."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

if __package__:
    from .sync_lean import _atomic_write_text
else:
    from sync_lean import _atomic_write_text

ROOT = Path(__file__).resolve().parents[1]
REVISION = "769ae44ffa5a640f43c699548cbdd87ddc63f998"
ITEMS = {
    "zero_smul_eq_zero": ("thm-zero-times-vector", "lean-zero-times-vector"),
    "double_negation": ("exr-double-negation", "lean-double-negation"),
    "add_inv_swap": ("exr-add-inv-swap", "lean-add-inv-swap"),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "lean/latex/main.tex")
    parser.add_argument("--output", type=Path, default=ROOT / "lean/latex")
    args = parser.parse_args(argv)
    raw = args.source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != "35bd2200db814a7636a101045c7a93bf17ec4fb60e1ea73fd7c4351b2dc771f9":
        parser.error("input does not match the pinned source main.tex")
    source = raw.decode("utf-8")
    output = args.output.absolute()
    filesystem = Path(output.anchor)
    metadata = {
        "source_repository": "https://github.com/nvantine/notes-and-exercises",
        "source_revision": REVISION,
        "source_file": "main.tex",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "context": "import Mathlib\nvariable {V : Type*} [AddCommGroup V] [Module ℝ V]\n",
        "compiler_checked": False,
        "items": [],
    }
    for box in re.finditer(r"\\begin\{leanbox\}(.*?)\\end\{leanbox\}", source, re.S):
        minted = re.search(r"\\begin\{minted\}\{lean4\}\n(.*?)\\end\{minted\}", box[1], re.S)
        link = re.search(r"\\href\{(https://live\.lean-lang\.org/#codez=[^}]+)\}", box[1])
        assert minted is not None and link is not None, "Lean box missing code or playground"
        code, url = minted[1], link[1]
        declaration = re.search(r"theorem (\w+)", code)
        assert declaration is not None, "Lean box missing theorem declaration"
        name = declaration[1]
        math_id, lean_id = ITEMS[name]
        start = source.count("\n", 0, box.start(1) + minted.start(1)) + 1
        lean_file, html_file = f"{name}.lean", f"{name}.html"
        _atomic_write_text(filesystem, output / lean_file, code)
        tokens = highlight(
            code, get_lexer_by_name("lean4", stripnl=False, ensurenl=False),
            HtmlFormatter(nowrap=True),
        )
        rendered = (
            '<div class="latex-lean-snippet">\n'
            f'<pre class="lean4"><code>{tokens}</code></pre>\n'
            f'<p><a href="{html.escape(url, quote=True)}">Open in Lean playground</a></p>\n'
            '</div>\n'
        )
        _atomic_write_text(filesystem, output / html_file, rendered)
        metadata["items"].append({
            "name": name, "math_id": math_id, "lean_id": lean_id,
            "lean_file": lean_file, "html_file": html_file,
            "source_lines": [start, start + code.count("\n") - 1],
            "sha256": hashlib.sha256(code.encode("utf-8")).hexdigest(),
            "playground_url": url,
        })
    _atomic_write_text(
        filesystem, output / "items.json",
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
    )
    print(f"Imported {len(metadata['items'])} display-only Lean snippets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
