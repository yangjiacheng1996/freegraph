# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B23F1 · 一键验收脚本的常驻门禁。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_the_b23f1_one_click_acceptance_script_passes() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "harness" / "verification" / "B23F1" / "acceptance.py"
    assert script.is_file(), f"缺一键验收脚本：{script}"
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(repo_root),
        env={**os.environ, "PYTHONPATH": str(repo_root / "src")},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "B23F1 acceptance: PASS" in proc.stdout
