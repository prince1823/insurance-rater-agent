"""The committed rulepacks must be exactly what the compiler produces from the
source grids -- guards against hand-edited / stale rulepacks."""
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent


def test_rulepacks_match_source_grids():
    r = subprocess.run(
        [sys.executable, "-m", "tools.compile_grids", "--check"],
        cwd=BACKEND, capture_output=True, text=True,
    )
    assert r.returncode == 0, f"rulepacks drifted from source grids:\n{r.stdout}\n{r.stderr}"
