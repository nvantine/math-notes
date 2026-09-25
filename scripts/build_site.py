"""Render a subject directory as its own Quarto book, then assemble one website."""
import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUBJECTS = ("linear-algebra", "convex-optimization", "analysis", "foundations")
SHARED = ("_shared.yml", "styles.css", "references.bib", "xref-math.html", "disclosures.html", "proofs.lua")


def build_site(root: Path = ROOT) -> Path:
    """Stage isolated projects; publish output only after every render succeeds."""
    workspace = root / ".build"
    workspace.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="books-", dir=workspace) as temporary:
        staging = Path(temporary)
        assembled = staging / "assembled"
        for subject in (None, *SUBJECTS):
            project = staging / (subject or "home")
            project.mkdir()
            source = root / subject if subject else root
            for path in source.glob("*.qmd"):
                shutil.copy2(path, project / path.name)
            shutil.copy2(source / "_quarto.yml", project / "_quarto.yml")
            for name in SHARED:
                shutil.copy2(root / name, project / name)
            # Imported Lean excerpts remain checked-in, offline display assets.
            if (root / "lean" / "latex").exists():
                shutil.copytree(root / "lean" / "latex", project / "lean" / "latex")
            subprocess.run(["quarto", "render"], cwd=project, check=True)
            destination = assembled / subject if subject else assembled
            shutil.copytree(project / "_site", destination)
        (assembled / ".nojekyll").touch()
        output = root / "_site"
        if output.exists():
            shutil.rmtree(output)
        shutil.copytree(assembled, output)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    print(f"Site built: {build_site()}")


if __name__ == "__main__":
    main()
