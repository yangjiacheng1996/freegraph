# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""B8F2 · 一键验收脚本的常驻门禁（T059）。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_the_b8f2_one_click_acceptance_script_passes() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "harness" / "verification" / "B8F2" / "acceptance.py"
    assert script.is_file(), f"缺一键验收脚本：{script}"
    env = {
        **os.environ,
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "B8F2 acceptance: PASS" in proc.stdout
