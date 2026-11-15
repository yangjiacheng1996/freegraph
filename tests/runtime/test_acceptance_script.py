# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B13F1 · 验收脚本 / README 的软断言升级（A3 / SC-005 / FR-021 / FR-032）。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def test_graph_core_exits_two_when_the_facade_is_not_ready() -> None:
    """M1 门面未就绪 ⇒ ``graph_core.py`` 以退出码 2 结束（不判 FAIL · EV-1）。"""
    env = {
        **os.environ,
        "PYTHONPATH": str(_REPO_ROOT / "src"),
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    proc = subprocess.run(
        [sys.executable, str(_REPO_ROOT / "harness" / "demo" / "graph_core.py")],
        cwd=str(_REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "[环境未就绪]" in proc.stdout


def test_graph_core_recursion_case_uses_the_hard_assertion() -> None:
    """``case_recursion_limit`` 使用 ``check`` + ``GraphRecursionError``（FR-021）。"""
    source = (_REPO_ROOT / "harness" / "demo" / "graph_core.py").read_text(
        encoding="utf-8"
    )
    case = source.split("def case_recursion_limit()", 1)[1].split(
        "def case_run_config_and_context()", 1
    )[0]
    assert "soft(" not in case
    assert "GraphRecursionError" in case
    assert "check(True" in case


def test_readme_soft_assertion_list_no_longer_mentions_recursion_limit() -> None:
    """README 软断言清单移除 ``recursion_limit`` 行，保留 C25（FR-032）。"""
    readme = (_REPO_ROOT / "harness" / "demo" / "README.md").read_text(
        encoding="utf-8"
    )
    assert "recursion_limit` 的载体" not in readme
    assert "C25 节点别名的调用形态" in readme
    assert "当前一处" in readme


def test_b13f1_one_click_acceptance_script_passes() -> None:
    """`harness/verification/B13F1/acceptance.py` 一键验收 PASS（V1–V10）。"""
    env = {
        **os.environ,
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    proc = subprocess.run(
        [sys.executable, str(_REPO_ROOT / "harness" / "verification" / "B13F1" / "acceptance.py")],
        cwd=str(_REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "B13F1 acceptance: PASS" in proc.stdout
