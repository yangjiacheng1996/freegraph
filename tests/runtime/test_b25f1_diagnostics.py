# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B25F1 · `harness/demo/diagnostics.py` 退出码与三组标记。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "harness" / "demo" / "diagnostics.py"
_SRC = _REPO_ROOT / "src"


def _run() -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(_SRC), "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(
        [sys.executable, str(_SCRIPT)],
        cwd=_REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )


def test_diagnostics_script_passes() -> None:
    proc = _run()
    if proc.returncode == 2:
        pytest.skip(f"diagnostics 环境未就绪：\n{proc.stdout}\n{proc.stderr}")
    output = (proc.stdout or "") + (proc.stderr or "")
    assert proc.returncode == 0, output
    assert "[trace]" in output
    assert "[checkpoint]" in output
    assert "[time_travel]" in output
    assert output.strip().splitlines()[-1] == "diagnostics: PASS"
