# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B16F1 · SC-018 文档守卫（demo README / target.py / 下游接线）。"""

from __future__ import annotations

import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_README = REPO_ROOT / "harness" / "demo" / "README.md"
TARGET = REPO_ROOT / "harness" / "demo" / "target.py"
README = REPO_ROOT / "README.md"

TARGET_SHA256 = "2bd47c225645f9ed7e991577d2a118b5eea8d4ab8e3b43b9e0e50539ac202991"


def test_demo_readme_locks_update_state_signature() -> None:
    text = DEMO_README.read_text(encoding="utf-8")
    assert "`update_state(...)` 的签名" in text
    assert "B16F1 未说签名" not in text
    assert "已锁定（B16F1）" in text
    assert "(config, values, as_node=None) -> RunConfig" in text


def test_target_py_is_unchanged() -> None:
    digest = hashlib.sha256(TARGET.read_bytes()).hexdigest()
    assert digest == TARGET_SHA256


def test_readme_marks_update_state_and_time_travel_delivered() -> None:
    text = README.read_text(encoding="utf-8")
    assert "update_state" in text
    assert "时间旅行已交付" in text


def test_downstream_prompts_are_wired() -> None:
    for name in (
        "B24F1_打包分发与兼容矩阵.md",
        "B25F1_双跑验收与迁移说明.md",
        "B20F1_本地Trace存储JSONL.md",
        "B20F2_Trace查询API与SQLite后端.md",
    ):
        path = REPO_ROOT / "harness" / "features" / name
        text = path.read_text(encoding="utf-8")
        assert "下游承接（B16F1" in text, name
