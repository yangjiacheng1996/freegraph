# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B25F1 · 固定脚本只读基准守卫（SHA-256 + 基线 ref diff）。"""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TARGET = _REPO_ROOT / "harness" / "demo" / "target.py"
_SHA_FILE = _REPO_ROOT / "tests" / "runtime" / "data" / "b25f1_target_py.sha256"


def _recorded_sha256() -> str:
    text = _SHA_FILE.read_text(encoding="utf-8").strip()
    digest = text.split()[0]
    assert len(digest) == 64 and digest == digest.lower()
    return digest


def test_target_py_matches_recorded_sha256() -> None:
    actual = hashlib.sha256(_TARGET.read_bytes()).hexdigest()
    assert actual == _recorded_sha256(), (
        "harness/demo/target.py 内容与入库 SHA-256 不一致 —— 只读基准被修改"
    )


def test_target_py_matches_baseline_ref() -> None:
    baseline = os.environ.get("B25F1_BASELINE_REF", "origin/main")
    exists = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{baseline}^{{commit}}"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if exists.returncode != 0:
        pytest.skip(
            f"基线 ref {baseline!r} 不可用（浅克隆 / 无该 ref）——"
            " 保留 SHA-256 断言，MUST NOT 静默通过"
        )
    diff = subprocess.run(
        ["git", "diff", "--exit-code", baseline, "--", "harness/demo/target.py"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert diff.returncode == 0, (
        f"target.py 与基线 ref {baseline!r} 不一致：\n{diff.stdout}\n{diff.stderr}"
    )
