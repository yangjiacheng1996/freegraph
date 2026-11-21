# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B13F1 · 验收脚本 / README 的软断言升级（A3 / SC-005 / FR-021 / FR-032）。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def test_graph_core_succeeds_when_the_facade_is_ready() -> None:
    """**B7F3 已交付** ⇒ ``graph_core.py`` MUST **成功**（退出码 **0**）。

    ⚠️ **替换为反面断言**（B7F3 · 破冻结面 · 追认项 ⑤）⇒ ⇒ **判据只可更严**：
    原断言「退出码 == 2（未就绪）」⇒ ⇒ 反面「退出码 == **0**（就绪**且绿**）」
    ⇒ ⇒ **MUST NOT** 退化为「不再是 2」（⇒ 真失败 ``rc == 1`` 仍判绿 ⇒ **门禁失效**）
    ⇒ ⇒ **MUST NOT** 保留「``[环境未就绪]`` 文本检查」（该文本**只在未就绪分支**打印
    ⇒ ⇒ invoke 交付后**永不出现** ⇒ ⇒ 与「退出码 == 0」**互斥**）。

    ✅ **拆分而不删**：subprocess **机制**断言（仍以子进程跑脚本并断言其退出码）**保留**。
    """
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
    assert proc.returncode == 0, proc.stdout + proc.stderr


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


def test_readme_soft_assertion_list_no_longer_mentions_retired_items() -> None:
    """README 软断言清单移除 ``recursion_limit`` 行与 C25 行（C25 已正式作废）。"""
    readme = (_REPO_ROOT / "harness" / "demo" / "README.md").read_text(
        encoding="utf-8"
    )
    assert "recursion_limit` 的载体" not in readme
    assert "C25 节点别名的调用形态" not in readme
    assert "当前一处" not in readme
    assert "当前零处" in readme


def test_graph_core_c21_context_case_uses_hard_assertion() -> None:
    """``case_run_config_and_context`` 的 C21 段 MUST 为硬断言（无 ``soft(``）。"""
    source = (_REPO_ROOT / "harness" / "demo" / "graph_core.py").read_text(
        encoding="utf-8"
    )
    case = source.split("def case_run_config_and_context()", 1)[1].split(
        "\ndef _invoke_ready()", 1
    )[0]
    assert "soft(" not in case
    assert "check(" in case or "eq(" in case


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


def test_b8f3_one_click_acceptance_script_passes() -> None:
    """`harness/verification/B8F3/acceptance.py` 一键验收 PASS（A1…A7）。"""
    env = {
        **os.environ,
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    proc = subprocess.run(
        [
            sys.executable,
            str(_REPO_ROOT / "harness" / "verification" / "B8F3" / "acceptance.py"),
            "--skip-differential",
        ],
        cwd=str(_REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "B8F3 acceptance: PASS" in proc.stdout


def test_b18f1_one_click_acceptance_script_passes() -> None:
    """`harness/verification/B18F1/acceptance.py` 一键验收 PASS（A1–A7）。"""
    env = {
        **os.environ,
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    proc = subprocess.run(
        [
            sys.executable,
            str(_REPO_ROOT / "harness" / "verification" / "B18F1" / "acceptance.py"),
        ],
        cwd=str(_REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "B18F1 acceptance: PASS" in proc.stdout


def test_b19f1_one_click_acceptance_script_passes() -> None:
    """`harness/verification/B19F1/acceptance.py` 一键验收 PASS（A1–A7）。"""
    env = {
        **os.environ,
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    proc = subprocess.run(
        [
            sys.executable,
            str(_REPO_ROOT / "harness" / "verification" / "B19F1" / "acceptance.py"),
        ],
        cwd=str(_REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "B19F1 acceptance: PASS" in proc.stdout


def test_b20f1_one_click_acceptance_script_passes() -> None:
    """`harness/verification/B20F1/acceptance.py` 一键验收 PASS（A1–A5）。"""
    env = {
        **os.environ,
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    proc = subprocess.run(
        [
            sys.executable,
            str(_REPO_ROOT / "harness" / "verification" / "B20F1" / "acceptance.py"),
        ],
        cwd=str(_REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "B20F1 acceptance: PASS" in proc.stdout
