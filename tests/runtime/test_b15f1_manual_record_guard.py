# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B15F1 · 人工验证记录守卫（SC-020 · 宪法原则 VI v1.13.0）。

断言记录**存在**、五段齐全、含**非空**实测输出（「符合预期」之类不算）、含追认文字；
并断言 B25F1 的下游承接为「复验」口径。
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RECORD = REPO_ROOT / "harness" / "verification" / "B15F1" / "manual-verification.md"
B25 = REPO_ROOT / "harness" / "features" / "B25F1_双跑验收与迁移说明.md"


def test_manual_record_exists_with_five_sections() -> None:
    assert RECORD.exists(), f"missing manual verification record: {RECORD}"
    text = RECORD.read_text(encoding="utf-8")
    for heading in ("## 1. 环境", "## 2. 步骤", "## 3. 实际输出", "## 4. 结论", "## 5. 遗留问题"):
        assert heading in text, heading


def test_manual_record_has_non_empty_fake_round_evidence() -> None:
    text = RECORD.read_text(encoding="utf-8")
    # fake 轮的实测输出（非「符合预期」之类空话）
    assert "fake 轮" in text
    assert "history len: 3" in text
    assert "events: 3" in text
    assert "database is locked" in text


def test_manual_record_has_unique_ratification_text() -> None:
    text = RECORD.read_text(encoding="utf-8")
    assert "R-3" in text and "R-13" in text
    assert "唯一一次" in text


def test_b25_downstream_is_reverification_not_replacement() -> None:
    assert B25.exists(), B25
    text = B25.read_text(encoding="utf-8")
    assert "下游承接（B15F1）" in text
    assert "复验" in text
