# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B23F1 · 人工验证记录的自动守卫（宪法 v1.13.0）。"""

from __future__ import annotations

from pathlib import Path


def test_the_b23f1_manual_verification_record_is_non_empty() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    record = repo_root / "harness" / "verification" / "B23F1" / "manual-verification.md"
    assert record.is_file(), f"缺人工验证记录：{record}"
    text = record.read_text(encoding="utf-8")
    for heading in (
        "## 1. 环境",
        "## 2. 步骤与实际输出",
        "## 3. 差分与一键验收",
        "## 4. 结论",
        "## 5. 遗留问题",
    ):
        assert heading in text, heading
    assert "B23F1 acceptance: PASS" in text
    assert "T-1" in text
    assert "_待填_" not in text
