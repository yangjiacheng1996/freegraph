# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B25F1 · 一键验收脚本（``--skip-real``）退出码与末行。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "harness" / "verification" / "B25F1" / "acceptance.py"
_SRC = _REPO_ROOT / "src"


def test_b25f1_acceptance_skip_real() -> None:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("LANGSMITH_")
    }
    env.update(
        {
            "PYTHONPATH": str(_SRC),
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), "--skip-real"],
        cwd=_REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode == 2:
        pytest.skip(f"B25F1 acceptance 环境未就绪：\n{output}")
    assert proc.returncode == 0, output
    assert output.strip().splitlines()[-1] == "B25F1 acceptance: PASS"
