import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def built_site():
    subprocess.run(["uv", "run", "python", "scripts/build_site.py"], cwd=ROOT, check=True)
    return ROOT / "_site"
